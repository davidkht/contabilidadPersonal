"""Salud del servicio (público)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api import schemas
from src.api.commons import RequestContext, get_request_context
from src.core.response import ApiResponse, ResponseMeta

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=ApiResponse[schemas.Health],
    summary="Comprobar que la API está viva",
    response_model_exclude_none=True,
)
def health(
    ctx: RequestContext = Depends(get_request_context),
) -> ApiResponse[schemas.Health]:
    return ApiResponse(data=schemas.Health(), meta=ResponseMeta(request_id=ctx.request_id))
