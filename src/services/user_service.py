"""Administración de cuentas de acceso."""

from __future__ import annotations

from datetime import UTC, datetime

from src.core.exceptions import Conflict, NotFound, ValidationFailed
from src.core.security import generate_password, hash_password
from src.models.enums import Role
from src.ports.repositories import UnitOfWork, UnitOfWorkFactory
from src.services._common import get_persona_or_404, require_admin, validate_username
from src.services.dto.commons import CredencialesRead
from src.services.dto.users import (
    CreateUserCommand,
    ListUsersQuery,
    ResetPasswordCommand,
    UpdateUserCommand,
    UserAccountRead,
)


def _read(user) -> UserAccountRead:
    now = datetime.now(UTC)
    return UserAccountRead(
        id=user.id,
        username=user.username,
        role=user.role.value,
        persona_id=user.persona_id,
        persona_nombre=user.persona_nombre,
        activo=user.activo,
        debe_cambiar_password=user.debe_cambiar_password,
        bloqueado=bool(user.bloqueado_hasta and user.bloqueado_hasta > now),
        ultimo_login=user.ultimo_login,
        creado_en=user.creado_en,
    )


def _get_user_or_404(uow: UnitOfWork, user_id: int):
    user = uow.users.get(user_id)
    if user is None:
        raise NotFound("Usuario no encontrado")
    return user


class UserService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    def list_users(self, dto: ListUsersQuery) -> list[UserAccountRead]:
        require_admin(dto.actor)
        with self._uow() as uow:
            return [_read(u) for u in uow.users.list_all()]

    def create_user(self, dto: CreateUserCommand) -> CredencialesRead:
        require_admin(dto.context)
        req = dto.request
        username = validate_username(req.username)
        try:
            role = Role(req.role)
        except ValueError as exc:
            raise ValidationFailed("Rol inválido") from exc
        if role is Role.USUARIO and req.persona_id is None:
            raise ValidationFailed("Un usuario con rol 'usuario' debe estar asociado a una persona")
        password = generate_password()
        with self._uow() as uow:
            if uow.users.username_taken(username):
                raise Conflict(f"El usuario '{username}' ya existe")
            if req.persona_id is not None:
                get_persona_or_404(uow, req.persona_id)
                if uow.users.get_by_persona(req.persona_id):
                    raise Conflict("Esa persona ya tiene una cuenta")
            user_id = uow.users.add(
                username=username,
                password_hash=hash_password(password),
                role=role,
                persona_id=req.persona_id,
                debe_cambiar_password=True,
            )
            uow.commit()
        return CredencialesRead(user_id=user_id, username=username, password_temporal=password)

    def update_user(self, dto: UpdateUserCommand) -> UserAccountRead:
        require_admin(dto.context)
        req = dto.request
        with self._uow() as uow:
            user = _get_user_or_404(uow, dto.user_id)
            fields: dict[str, object] = {}
            if req.username is not None:
                username = validate_username(req.username)
                if username != user.username.lower() and uow.users.username_taken(username):
                    raise Conflict(f"El usuario '{username}' ya existe")
                fields["username"] = username
            if req.activo is not None and req.activo != user.activo:
                if not req.activo:
                    if user.id == dto.context.user_id:
                        raise ValidationFailed("No puedes desactivar tu propia cuenta")
                    if user.role is Role.ADMIN and uow.users.count_admins() <= 1:
                        raise ValidationFailed("Debe quedar al menos un administrador activo")
                    fields["token_version"] = user.token_version + 1  # cierra sus sesiones
                fields["activo"] = req.activo
            uow.users.update(user.id, fields)
            uow.commit()
            return _read(uow.users.get(user.id))

    def reset_password(self, dto: ResetPasswordCommand) -> CredencialesRead:
        """Genera una contraseña temporal nueva, desbloquea la cuenta y cierra sus sesiones."""
        require_admin(dto.context)
        password = generate_password()
        with self._uow() as uow:
            user = _get_user_or_404(uow, dto.user_id)
            uow.users.update(
                user.id,
                {
                    "password_hash": hash_password(password),
                    "debe_cambiar_password": True,
                    "token_version": user.token_version + 1,
                    "intentos_fallidos": 0,
                    "bloqueado_hasta": None,
                },
            )
            uow.commit()
        return CredencialesRead(user_id=user.id, username=user.username, password_temporal=password)
