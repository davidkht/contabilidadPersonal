from __future__ import annotations

from datetime import datetime

from pydantic import Field

from src.services.dto.commons import ActorContext, MutationAuditContext, ServiceDto


class LoginCommand(ServiceDto):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)
    ip_address: str | None = None


class CurrentUserRead(ServiceDto):
    id: int
    username: str
    role: str
    persona_id: int | None
    persona_nombre: str | None
    debe_cambiar_password: bool


class LoginResult(ServiceDto):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: CurrentUserRead


class ResolveTokenQuery(ServiceDto):
    token: str


class GetCurrentUserQuery(ServiceDto):
    actor: ActorContext


class ChangePasswordCommand(ServiceDto):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)
    context: MutationAuditContext
