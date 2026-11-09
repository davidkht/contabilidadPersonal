"""Administración de personas, sus movimientos, su analítica y la aplicación de intereses."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query, status

from src.api import schemas, wire_enums
from src.api.commons import RequestContext, get_request_context, wire_response
from src.api.deps import get_analytics_service, get_movimiento_service, get_persona_service
from src.api.security import actor, mutation_audit, require_admin
from src.core.auth import TokenPayload
from src.core.response import ApiResponse, ResponseMeta, paginated
from src.services.analytics_service import AnalyticsService
from src.services.dto.analytics import PersonaAnaliticaQuery
from src.services.dto.movimientos import (
    AplicarInteresesCommand,
    DeleteMovimientoCommand,
    ListMovimientosQuery,
    RegistrarMovimientoCommand,
)
from src.services.dto.movimientos import (
    RegistrarMovimientoRequest as RegistrarMovimientoRequestDto,
)
from src.services.dto.personas import (
    CreatePersonaCommand,
    DeletePersonaCommand,
    GetPersonaQuery,
    ListPersonasQuery,
    UpdatePersonaCommand,
)
from src.services.dto.personas import CreatePersonaRequest as CreatePersonaRequestDto
from src.services.dto.personas import UpdatePersonaRequest as UpdatePersonaRequestDto
from src.services.movimiento_service import MovimientoService
from src.services.persona_service import PersonaService

router = APIRouter(prefix="/admin", tags=["admin: personas"])


# ─── Personas ─────────────────────────────────────────────────────────────────


@router.get(
    "/personas",
    response_model=ApiResponse[list[schemas.Persona]],
    summary="Listar personas",
    response_model_exclude_none=True,
)
def list_personas(
    buscar: str | None = Query(default=None, max_length=100),
    solo_con_saldo: bool = Query(default=False),
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    persona_service: PersonaService = Depends(get_persona_service),
) -> ApiResponse[list[schemas.Persona]]:
    dto = ListPersonasQuery(actor=actor(user), buscar=buscar or None, solo_con_saldo=solo_con_saldo)
    result = persona_service.list_personas(dto)
    return ApiResponse(
        data=[wire_response(schemas.Persona, row) for row in result],
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.post(
    "/personas",
    response_model=ApiResponse[schemas.CreatePersonaResult],
    status_code=status.HTTP_201_CREATED,
    summary="Crear persona (y opcionalmente su cuenta de usuario)",
    description="Si se crea la cuenta, `credenciales` trae la contraseña temporal (una sola vez); "
    "si no, `credenciales` es `null`.",
)
def create_persona(
    body: schemas.CreatePersonaRequest,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    persona_service: PersonaService = Depends(get_persona_service),
) -> ApiResponse[schemas.CreatePersonaResult]:
    dto = CreatePersonaCommand(
        request=CreatePersonaRequestDto(**body.model_dump()),
        context=mutation_audit(user, ctx),
    )
    result = persona_service.create_persona(dto)
    return ApiResponse(
        data=wire_response(schemas.CreatePersonaResult, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.get(
    "/personas/{persona_id}",
    response_model=ApiResponse[schemas.Persona],
    summary="Obtener una persona",
    response_model_exclude_none=True,
)
def get_persona(
    persona_id: int,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    persona_service: PersonaService = Depends(get_persona_service),
) -> ApiResponse[schemas.Persona]:
    dto = GetPersonaQuery(actor=actor(user), persona_id=persona_id)
    result = persona_service.get_persona(dto)
    return ApiResponse(
        data=wire_response(schemas.Persona, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.patch(
    "/personas/{persona_id}",
    response_model=ApiResponse[schemas.Persona],
    summary="Actualizar parcialmente una persona",
    description="Solo cambian los campos enviados; `null` borra un campo opcional.",
    response_model_exclude_none=True,
)
def update_persona(
    persona_id: int,
    body: schemas.UpdatePersonaRequest,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    persona_service: PersonaService = Depends(get_persona_service),
) -> ApiResponse[schemas.Persona]:
    dto = UpdatePersonaCommand(
        persona_id=persona_id,
        request=UpdatePersonaRequestDto(**body.model_dump(exclude_unset=True)),
        fields_set=frozenset(body.model_fields_set),
        context=mutation_audit(user, ctx),
    )
    result = persona_service.update_persona(dto)
    return ApiResponse(
        data=wire_response(schemas.Persona, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.delete(
    "/personas/{persona_id}",
    response_model=ApiResponse[schemas.Deleted],
    summary="Eliminar una persona, sus movimientos y su cuenta",
    response_model_exclude_none=True,
)
def delete_persona(
    persona_id: int,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    persona_service: PersonaService = Depends(get_persona_service),
) -> ApiResponse[schemas.Deleted]:
    dto = DeletePersonaCommand(persona_id=persona_id, context=mutation_audit(user, ctx))
    persona_service.delete_persona(dto)
    return ApiResponse(data=schemas.Deleted(), meta=ResponseMeta(request_id=ctx.request_id))


# ─── Analítica por persona ────────────────────────────────────────────────────


@router.get(
    "/personas/{persona_id}/analitica",
    response_model=ApiResponse[schemas.PersonaAnalitica],
    summary="Analítica de la deuda de una persona",
    response_model_exclude_none=True,
)
def persona_analitica(
    persona_id: int,
    meses: int = Query(default=12, ge=1, le=120),
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> ApiResponse[schemas.PersonaAnalitica]:
    dto = PersonaAnaliticaQuery(actor=actor(user), persona_id=persona_id, meses=meses)
    result = analytics_service.persona_analitica(dto)
    return ApiResponse(
        data=wire_response(schemas.PersonaAnalitica, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


# ─── Movimientos ──────────────────────────────────────────────────────────────


@router.get(
    "/personas/{persona_id}/movimientos",
    response_model=ApiResponse[list[schemas.Movimiento]],
    summary="Movimientos de una persona (paginado)",
    response_model_exclude_none=True,
)
def list_movimientos(
    persona_id: int,
    limit: int = Query(default=500, ge=1, le=1000),
    cursor: str | None = Query(default=None, max_length=200),
    orden: wire_enums.Orden = Query(default=wire_enums.Orden.DESC),
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    movimiento_service: MovimientoService = Depends(get_movimiento_service),
) -> ApiResponse[list[schemas.Movimiento]]:
    dto = ListMovimientosQuery(
        actor=actor(user),
        persona_id=persona_id,
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


@router.post(
    "/personas/{persona_id}/movimientos",
    response_model=ApiResponse[schemas.Movimiento],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un movimiento (cargo, abono o ajuste)",
    response_model_exclude_none=True,
)
def registrar_movimiento(
    persona_id: int,
    body: schemas.RegistrarMovimientoRequest,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    movimiento_service: MovimientoService = Depends(get_movimiento_service),
) -> ApiResponse[schemas.Movimiento]:
    dto = RegistrarMovimientoCommand(
        persona_id=persona_id,
        request=RegistrarMovimientoRequestDto(
            monto=body.monto,
            descripcion=body.descripcion,
            fecha=body.fecha,
            tipo=body.tipo.value if body.tipo else None,
        ),
        context=mutation_audit(user, ctx),
    )
    result = movimiento_service.registrar(dto)
    return ApiResponse(
        data=wire_response(schemas.Movimiento, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )


@router.delete(
    "/personas/{persona_id}/movimientos/{movimiento_id}",
    response_model=ApiResponse[schemas.Deleted],
    summary="Eliminar un movimiento",
    response_model_exclude_none=True,
)
def eliminar_movimiento(
    persona_id: int,
    movimiento_id: int,
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    movimiento_service: MovimientoService = Depends(get_movimiento_service),
) -> ApiResponse[schemas.Deleted]:
    dto = DeleteMovimientoCommand(
        persona_id=persona_id,
        movimiento_id=movimiento_id,
        context=mutation_audit(user, ctx),
    )
    movimiento_service.eliminar(dto)
    return ApiResponse(data=schemas.Deleted(), meta=ResponseMeta(request_id=ctx.request_id))


@router.post(
    "/intereses/aplicar",
    response_model=ApiResponse[schemas.AplicarInteresesResult],
    summary="Aplicar intereses pendientes a todas las personas",
    description="Idempotente en el mismo día: el cargo de interés crea un movimiento nuevo.",
    response_model_exclude_none=True,
)
def aplicar_intereses(
    body: schemas.AplicarInteresesRequest | None = Body(default=None),
    user: TokenPayload = Depends(require_admin),
    ctx: RequestContext = Depends(get_request_context),
    movimiento_service: MovimientoService = Depends(get_movimiento_service),
) -> ApiResponse[schemas.AplicarInteresesResult]:
    dto = AplicarInteresesCommand(
        context=mutation_audit(user, ctx),
        fecha_corte=body.fecha_corte if body else None,
    )
    result = movimiento_service.aplicar_intereses(dto)
    return ApiResponse(
        data=wire_response(schemas.AplicarInteresesResult, result),
        meta=ResponseMeta(request_id=ctx.request_id),
    )
