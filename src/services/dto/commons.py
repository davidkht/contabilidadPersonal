from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ServiceDto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ActorContext(ServiceDto):
    """Quién realiza la operación (derivado del JWT)."""

    user_id: int
    role: str  # "admin" | "usuario"
    persona_id: int | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class MutationAuditContext(ActorContext):
    ip_address: str | None = None
    user_agent: str | None = None


class CredencialesRead(ServiceDto):
    """Credenciales en claro: solo se devuelven una vez al crear/restablecer."""

    user_id: int
    username: str
    password_temporal: str
