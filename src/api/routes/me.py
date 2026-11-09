"""Vista del usuario final: su propia deuda (analítica y movimientos)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api import schemas, wire_enums
from src.api.commons import RequestContext, get_request_context, wire_response
from src.api.deps import get_analytics_service, get_movimiento_service
from src.api.security import actor, require_user
from src.core.auth import TokenPayload
from src.core.exceptions import NotFound
from src.core.response import ApiResponse, ResponseMeta, paginated
from src.services.analytics_service import AnalyticsService
from src.services.dto.analytics import MiAnaliticaQuery
from src.services.dto.movimientos import ListMovimientosQuery
from src.services.movimiento_service import MovimientoService

router = APIRouter(prefix="/me", tags=["me"])


@router.get(
    "/analitica",
    response_model=ApiResponse[schemas.PersonaAnalitica],
    summary="Analítica de mi deuda",
    description="404 si la cuenta no está vinculada a una persona (p. ej. el admin).",
    response_model_exclude_none=True,
)
def mi_analitica(
    meses: int = Query(default=12, ge=1, le=120),
    user: TokenPayload = Depends(require_user),
    ctx: RequestContext = Depends(get_request_context),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> ApiResponse[schemas.PersonaAnalitica]:
    dto = MiAnaliticaQuery(actor=actor(user), meses=meses)
    result = analytics_service.mi_analitica(dto)
    return ApiResponse(
        data=wire_response(schemas.PersonaAnalitica, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.get(
    "/movimientos",
    response_model=ApiResponse[list[schemas.Movimiento]],
    summary="Mis movimientos (paginado)",
    description="404 si la cuenta no está vinculada a una persona.",
    response_model_exclude_none=True,
)
def mis_movimientos(
    limit: int = Query(default=500, ge=1, le=1000),
    cursor: str | None = Query(default=None, max_length=200),
    orden: wire_enums.Orden = Query(default=wire_enums.Orden.DESC),
    user: TokenPayload = Depends(require_user),
    ctx: RequestContext = Depends(get_request_context),
    movimiento_service: MovimientoService = Depends(get_movimiento_service),
) -> ApiResponse[list[schemas.Movimiento]]:
    if user.persona_id is None:
        raise NotFound("Tu cuenta no tiene una deuda asociada")
    dto = ListMovimientosQuery(
        actor=actor(user),
        persona_id=user.persona_id,
        limit=limit,
        cursor=cursor,
        orden=orden.value,
    )
    result = movimiento_service.list_movimientos(dto)
    items = [wire_response(schemas.Movimiento, row) for row in result.items]
    return paginated(
        items,
        next_cursor=result.next_cursor,
        limit=limit,
        total=result.total,
        request_id=ctx.request_id,
    )
