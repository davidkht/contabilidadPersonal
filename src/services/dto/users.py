from __future__ import annotations

from datetime import datetime

from pydantic import Field

from src.services.dto.commons import ActorContext, MutationAuditContext, ServiceDto


class UserAccountRead(ServiceDto):
    id: int
    username: str
    role: str
    persona_id: int | None
    persona_nombre: str | None
    activo: bool
    debe_cambiar_password: bool
    bloqueado: bool
    ultimo_login: datetime | None
    creado_en: datetime


class ListUsersQuery(ServiceDto):
    actor: ActorContext


class CreateUserRequest(ServiceDto):
    username: str = Field(min_length=3, max_length=60)
    role: str  # "admin" | "usuario"
    persona_id: int | None = None  # obligatorio para "usuario"


class CreateUserCommand(ServiceDto):
    request: CreateUserRequest
    context: MutationAuditContext


class UpdateUserRequest(ServiceDto):
    username: str | None = Field(default=None, min_length=3, max_length=60)
    activo: bool | None = None


class UpdateUserCommand(ServiceDto):
    user_id: int
    request: UpdateUserRequest
    context: MutationAuditContext


class ResetPasswordCommand(ServiceDto):
    user_id: int
    context: MutationAuditContext
