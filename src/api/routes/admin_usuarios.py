"""Administración de cuentas de usuario."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api import schemas
from src.api.commons import RequestContext, get_request_context, wire_response
from src.api.deps import get_user_service
from src.api.security import actor, mutation_audit, require_admin
from src.core.auth import TokenPayload
from src.core.response import ApiResponse, ResponseMeta
from src.services.dto.users import (
    CreateUserCommand,
    ListUsersQuery,
    ResetPasswordCommand,
    UpdateUserCommand,
)
from src.services.dto.users import CreateUserRequest as CreateUserRequestDto
from src.services.dto.users import UpdateUserRequest as UpdateUserRequestDto
from src.services.user_service import UserService

router = APIRouter(prefix="/admin/usuarios", tags=["admin: usuarios"])


@router.get(
    "",
    response_model=ApiResponse[list[schemas.UserAccount]],
    summary="Listar cuentas de usuario",
    response_model_exclude_none=True,
)
def list_usuarios(
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[list[schemas.UserAccount]]:
    dto = ListUsersQuery(actor=actor(user))
    result = user_service.list_users(dto)
    return ApiResponse(
        data=[wire_response(schemas.UserAccount, row) for row in result],
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.post(
    "",
    response_model=ApiResponse[schemas.Credenciales],
    status_code=status.HTTP_201_CREATED,
    summary="Crear una cuenta (devuelve la contraseña temporal una sola vez)",
    response_model_exclude_none=True,
)
def create_usuario(
    body: schemas.CreateUserRequest,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[schemas.Credenciales]:
    dto = CreateUserCommand(
        request=CreateUserRequestDto(
            username=body.username, role=body.role.value, persona_id=body.persona_id
        ),
        context=mutation_audit(user, ctx),
    )
    result = user_service.create_user(dto)
    return ApiResponse(
        data=wire_response(schemas.Credenciales, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.patch(
    "/{user_id}",
    response_model=ApiResponse[schemas.UserAccount],
    summary="Renombrar o activar/desactivar una cuenta",
    description="Desactivar una cuenta revoca sus sesiones abiertas.",
    response_model_exclude_none=True,
)
def update_usuario(
    user_id: int,
    body: schemas.UpdateUserRequest,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[schemas.UserAccount]:
    dto = UpdateUserCommand(
        user_id=user_id,
        request=UpdateUserRequestDto(username=body.username, activo=body.activo),
        context=mutation_audit(user, ctx),
    )
    result = user_service.update_user(dto)
    return ApiResponse(
        data=wire_response(schemas.UserAccount, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.post(
    "/{user_id}/reset-password",
    response_model=ApiResponse[schemas.Credenciales],
    summary="Restablecer la contraseña (genera una temporal)",
    response_model_exclude_none=True,
)
def reset_password(
    user_id: int,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[schemas.Credenciales]:
    dto = ResetPasswordCommand(user_id=user_id, context=mutation_audit(user, ctx))
    result = user_service.reset_password(dto)
    return ApiResponse(
        data=wire_response(schemas.Credenciales, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )
