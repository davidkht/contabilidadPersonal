"""Autenticación en el borde HTTP: Bearer JWT -> ``TokenPayload`` + ``RequireRole``."""

from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from src.core.exceptions import AuthenticationFailed
from src.services.dto.auth import ResolveTokenQuery


class UserRole(StrEnum):
    ADMIN = "admin"
    USUARIO = "usuario"


ANY_USER = (UserRole.ADMIN, UserRole.USUARIO)
ADMIN_ONLY = (UserRole.ADMIN,)


class TokenPayload(BaseModel):
    """Identidad verificada (firma + expiración + versión de token contra la DB)."""

    model_config = ConfigDict(frozen=True)

    sub: int  # user id
    role: UserRole
    persona_id: int | None = None


_bearer = HTTPBearer(auto_error=False, description="JWT obtenido en POST /api/auth/login")


def get_token_payload(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TokenPayload:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationFailed("Falta el token de autenticación")
    actor = request.app.state.container.auth.resolve_token(
        ResolveTokenQuery(token=credentials.credentials)
    )
    return TokenPayload(sub=actor.user_id, role=UserRole(actor.role), persona_id=actor.persona_id)


class RequireRole:
    """Dependencia: exige un JWT válido con alguno de los roles indicados (403 si no)."""

    def __init__(self, roles: tuple[UserRole, ...]) -> None:
        self.roles = frozenset(roles)

    def __call__(self, user: TokenPayload = Depends(get_token_payload)) -> TokenPayload:
        if user.role not in self.roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Permiso denegado")
        return user
