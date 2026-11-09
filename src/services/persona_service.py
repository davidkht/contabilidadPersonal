"""Gestión de personas (deudores) y su cuenta de acceso asociada."""

from __future__ import annotations

from datetime import date

from src.core.exceptions import Conflict, ValidationFailed
from src.core.security import generate_password, hash_password
from src.models.enums import Role, TipoMovimiento
from src.ports.repositories import UnitOfWorkFactory
from src.services._common import (
    clean,
    get_persona_or_404,
    persona_read,
    require_admin,
    require_persona_access,
    slugify,
    to_centavos,
    unique_username,
    validate_username,
)
from src.services.dto.commons import CredencialesRead
from src.services.dto.personas import (
    CreatePersonaCommand,
    CreatePersonaResult,
    DeletePersonaCommand,
    GetPersonaQuery,
    ListPersonasQuery,
    PersonaRead,
    UpdatePersonaCommand,
)


class PersonaService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    def list_personas(self, dto: ListPersonasQuery) -> list[PersonaRead]:
        require_admin(dto.actor)
        with self._uow() as uow:
            personas = uow.personas.list_all()
            usernames = {u.persona_id: u.username for u in uow.users.list_all() if u.persona_id}
        if dto.buscar:
            needle = dto.buscar.casefold()
            personas = [
                p
                for p in personas
                if needle in p.nombre_completo.casefold() or needle in (p.documento or "")
            ]
        if dto.solo_con_saldo:
            personas = [p for p in personas if p.saldo_centavos != 0]
        return [persona_read(p, usernames.get(p.id)) for p in personas]

    def get_persona(self, dto: GetPersonaQuery) -> PersonaRead:
        require_persona_access(dto.actor, dto.persona_id)
        with self._uow() as uow:
            persona = get_persona_or_404(uow, dto.persona_id)
            user = uow.users.get_by_persona(persona.id)
        return persona_read(persona, user.username if user else None)

    def create_persona(self, dto: CreatePersonaCommand) -> CreatePersonaResult:
        require_admin(dto.context)
        req = dto.request
        nombre, apellido = clean(req.nombre), clean(req.apellido)
        if not nombre or not apellido:
            raise ValidationFailed("Nombre y apellido son obligatorios")
        monto = to_centavos(req.monto_inicial)
        hoy = date.today()
        credenciales = None
        with self._uow() as uow:
            if uow.personas.exists_name(nombre, apellido):
                raise Conflict(f"Ya existe una persona llamada {nombre} {apellido}")
            persona_id = uow.personas.add(
                nombre=nombre,
                apellido=apellido,
                documento=clean(req.documento),
                telefono=clean(req.telefono),
                email=clean(req.email),
                interes_mensual=req.interes_mensual,
                descripcion=clean(req.descripcion),
                fecha_inicio=hoy,
            )
            if monto != 0:
                uow.movimientos.add(
                    persona_id=persona_id,
                    fecha=hoy,
                    monto_centavos=monto,
                    tipo=TipoMovimiento.from_amount(monto),
                    descripcion=clean(req.descripcion) or "Saldo inicial",
                    creado_por=dto.context.user_id,
                )
            if req.crear_usuario:
                if req.username:
                    username = validate_username(req.username)
                    if uow.users.username_taken(username):
                        raise Conflict(f"El usuario '{username}' ya existe")
                else:
                    username = unique_username(uow, slugify(nombre, apellido))
                password = generate_password()
                user_id = uow.users.add(
                    username=username,
                    password_hash=hash_password(password),
                    role=Role.USUARIO,
                    persona_id=persona_id,
                    debe_cambiar_password=True,
                )
                credenciales = CredencialesRead(
                    user_id=user_id, username=username, password_temporal=password
                )
            uow.commit()
            persona = uow.personas.get(persona_id)
        return CreatePersonaResult(
            persona=persona_read(persona, credenciales.username if credenciales else None),
            credenciales=credenciales,
        )

    def update_persona(self, dto: UpdatePersonaCommand) -> PersonaRead:
        require_admin(dto.context)
        data = dto.request.model_dump()
        fields = {k: data[k] for k in dto.fields_set if k in data}
        for key in ("nombre", "apellido"):
            if key in fields:
                fields[key] = clean(fields[key])
                if not fields[key]:
                    raise ValidationFailed(f"{key} no puede estar vacío")
        for key in ("documento", "telefono", "email", "descripcion"):
            if key in fields:
                fields[key] = clean(fields[key])
        if "interes_mensual" in fields and fields["interes_mensual"] is None:
            fields["interes_mensual"] = 0.0
        with self._uow() as uow:
            persona = get_persona_or_404(uow, dto.persona_id)
            nombre = fields.get("nombre", persona.nombre)
            apellido = fields.get("apellido", persona.apellido)
            if uow.personas.exists_name(nombre, apellido, exclude_id=persona.id):
                raise Conflict(f"Ya existe una persona llamada {nombre} {apellido}")
            uow.personas.update(persona.id, fields)
            uow.commit()
            persona = uow.personas.get(persona.id)
            user = uow.users.get_by_persona(persona.id)
        return persona_read(persona, user.username if user else None)

    def delete_persona(self, dto: DeletePersonaCommand) -> None:
        """Borra la persona, sus movimientos y su cuenta (ON DELETE CASCADE)."""
        require_admin(dto.context)
        with self._uow() as uow:
            get_persona_or_404(uow, dto.persona_id)
            uow.personas.delete(dto.persona_id)
            uow.commit()
