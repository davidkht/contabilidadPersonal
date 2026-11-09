from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.enums import Role


@dataclass(slots=True)
class User:
    id: int
    username: str
    password_hash: str
    role: Role
    persona_id: int | None
    activo: bool
    debe_cambiar_password: bool
    token_version: int
    intentos_fallidos: int
    bloqueado_hasta: datetime | None
    ultimo_login: datetime | None
    creado_en: datetime
    persona_nombre: str | None = None
