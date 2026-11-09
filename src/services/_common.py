"""Utilidades compartidas por los servicios (dinero, mapeos, guardas de acceso)."""

from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal

from src.core.exceptions import NotFound, PermissionDenied, ValidationFailed
from src.models.movimiento import Movimiento
from src.models.persona import Persona
from src.ports.repositories import UnitOfWork
from src.services.dto.commons import ActorContext
from src.services.dto.movimientos import MovimientoRead
from src.services.dto.personas import PersonaRead

MAX_ABS_CENTAVOS = 10**15


def to_centavos(value: Decimal | float) -> int:
    try:
        cents = (Decimal(str(value)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise ValidationFailed("Monto inválido") from exc
    if not cents.is_finite() or abs(cents) > MAX_ABS_CENTAVOS:
        raise ValidationFailed("Monto fuera de rango")
    return int(cents)


def to_pesos(centavos: int) -> float:
    return round(centavos / 100, 2)


def persona_read(p: Persona, username: str | None = None) -> PersonaRead:
    return PersonaRead(
        id=p.id,
        nombre=p.nombre,
        apellido=p.apellido,
        nombre_completo=p.nombre_completo,
        documento=p.documento,
        telefono=p.telefono,
        email=p.email,
        interes_mensual=p.interes_mensual,
        descripcion=p.descripcion,
        fecha_inicio=p.fecha_inicio,
        creado_en=p.creado_en,
        saldo=to_pesos(p.saldo_centavos),
        num_movimientos=p.num_movimientos,
        ultimo_movimiento=p.ultimo_movimiento,
        username=username,
    )


def movimiento_read(m: Movimiento) -> MovimientoRead:
    return MovimientoRead(
        id=m.id,
        persona_id=m.persona_id,
        fecha=m.fecha,
        monto=to_pesos(m.monto_centavos),
        tipo=m.tipo.value,
        descripcion=m.descripcion,
        saldo=to_pesos(m.saldo_centavos) if m.saldo_centavos is not None else None,
        creado_en=m.creado_en,
    )


def require_admin(actor: ActorContext) -> None:
    if not actor.is_admin:
        raise PermissionDenied("Se requiere rol administrador")


def require_persona_access(actor: ActorContext, persona_id: int) -> None:
    """Un usuario solo puede ver su propia persona; el admin puede ver todas."""
    if actor.is_admin:
        return
    if actor.persona_id is None or actor.persona_id != persona_id:
        # 404 en vez de 403 para no revelar qué IDs existen.
        raise NotFound("Persona no encontrada")


def get_persona_or_404(uow: UnitOfWork, persona_id: int) -> Persona:
    persona = uow.personas.get(persona_id)
    if persona is None:
        raise NotFound("Persona no encontrada")
    return persona


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    return value or None


def slugify(*parts: str) -> str:
    text = ".".join(p for p in parts if p)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9.]+", ".", text.lower())
    return re.sub(r"\.{2,}", ".", text).strip(".") or "usuario"


USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,59}$")


def validate_username(username: str) -> str:
    username = username.strip().lower()
    if not USERNAME_RE.fullmatch(username):
        raise ValidationFailed(
            "Usuario inválido: 3-60 caracteres, minúsculas, números, '.', '_' o '-'"
        )
    return username


def unique_username(uow: UnitOfWork, base: str) -> str:
    candidate, n = base, 2
    while uow.users.username_taken(candidate):
        candidate, n = f"{base}{n}", n + 1
    return candidate


def validate_new_password(password: str, *, min_length: int, username: str) -> None:
    if len(password) < min_length:
        raise ValidationFailed(f"La contraseña debe tener al menos {min_length} caracteres")
    if password.lower() == username.lower():
        raise ValidationFailed("La contraseña no puede ser igual al usuario")
    if password.isdigit() or password.isalpha():
        raise ValidationFailed("La contraseña debe combinar letras y números o símbolos")
