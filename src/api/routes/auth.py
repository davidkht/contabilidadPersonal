"""Autenticación: login, usuario actual y cambio de contraseña."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api import schemas
from src.api.commons import RequestContext, get_request_context, wire_response
from src.api.deps import get_auth_service
from src.api.security import actor, mutation_audit, require_user
from src.core.auth import TokenPayload
from src.core.response import ApiResponse, ResponseMeta
from src.services.auth_service import AuthService
from src.services.dto.auth import ChangePasswordCommand, GetCurrentUserQuery, LoginCommand

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=ApiResponse[schemas.LoginResult],
    summary="Iniciar sesión (devuelve un JWT Bearer)",
    description="401 si las credenciales no son válidas; 429 si la cuenta está bloqueada.",
    response_model_exclude_none=True,
)
def login(
    body: schemas.LoginRequest,
    ctx: RequestContext = Depends(get_request_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiResponse[schemas.LoginResult]:
    dto = LoginCommand(username=body.username, password=body.password, ip_address=ctx.ip_address)
    result = auth_service.login(dto)
    return ApiResponse(
        data=wire_response(schemas.LoginResult, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.get(
    "/me",
    response_model=ApiResponse[schemas.CurrentUser],
    summary="Usuario autenticado actual",
    response_model_exclude_none=True,
)
def me(
    user: TokenPayload = Depends(require_user),
    ctx: RequestContext = Depends(get_request_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiResponse[schemas.CurrentUser]:
    dto = GetCurrentUserQuery(actor=actor(user))
    result = auth_service.get_current_user(dto)
    return ApiResponse(
        data=wire_response(schemas.CurrentUser, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.post(
    "/change-password",
    response_model=ApiResponse[schemas.LoginResult],
    summary="Cambiar la contraseña propia",
    description="Revoca todos los tokens anteriores y devuelve uno nuevo.",
    response_model_exclude_none=True,
)
def change_password(
    body: schemas.ChangePasswordRequest,
    user: TokenPayload = Depends(require_user),
    ctx: RequestContext = Depends(get_request_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiResponse[schemas.LoginResult]:
    dto = ChangePasswordCommand(
        current_password=body.current_password,
        new_password=body.new_password,
        context=mutation_audit(user, ctx),
    )
    result = auth_service.change_password(dto)
    return ApiResponse(
        data=wire_response(schemas.LoginResult, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )
