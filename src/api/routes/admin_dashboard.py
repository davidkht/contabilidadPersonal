"""Panel general del administrador."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api import schemas
from src.api.commons import RequestContext, get_request_context, wire_response
from src.api.deps import get_analytics_service
from src.api.security import actor, require_admin
from src.core.auth import TokenPayload
from src.core.response import ApiResponse, ResponseMeta
from src.services.analytics_service import AnalyticsService
from src.services.dto.analytics import DashboardQuery

router = APIRouter(prefix="/admin", tags=["admin: dashboard"])


@router.get(
    "/dashboard",
    response_model=ApiResponse[schemas.Dashboard],
    summary="Resumen global de deudas",
    response_model_exclude_none=True,
)
def dashboard(
    meses: int = Query(default=12, ge=1, le=120),
    top: int = Query(default=5, ge=1, le=50),
    recientes: int = Query(default=10, ge=0, le=100),
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> ApiResponse[schemas.Dashboard]:
    dto = DashboardQuery(actor=actor(user), meses=meses, top=top, recientes=recientes)
    result = analytics_service.dashboard(dto)
    return ApiResponse(
        data=wire_response(schemas.Dashboard, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )
