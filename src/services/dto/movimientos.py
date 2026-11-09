from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from src.services.dto.commons import ActorContext, MutationAuditContext, ServiceDto


class MovimientoRead(ServiceDto):
    id: int
    persona_id: int
    fecha: date
    monto: float  # pesos con signo
    tipo: str  # cargo | abono | interes | ajuste
    descripcion: str
    saldo: float | None  # saldo acumulado tras el movimiento
    creado_en: datetime


class ListMovimientosQuery(ServiceDto):
    actor: ActorContext
    persona_id: int
    limit: int = Field(default=500, ge=1, le=1000)
    cursor: str | None = None
    orden: Literal["asc", "desc"] = "desc"


class MovimientoPage(ServiceDto):
    items: list[MovimientoRead]
    next_cursor: str | None
    total: int


class RegistrarMovimientoRequest(ServiceDto):
    monto: Decimal  # positivo: aumenta la deuda; negativo: abono
    descripcion: str = Field(default="", max_length=500)
    fecha: date | None = None  # por defecto hoy
    tipo: str | None = None  # por defecto según el signo; "ajuste" permitido explícitamente


class RegistrarMovimientoCommand(ServiceDto):
    persona_id: int
    request: RegistrarMovimientoRequest
    context: MutationAuditContext


class DeleteMovimientoCommand(ServiceDto):
    persona_id: int
    movimiento_id: int
    context: MutationAuditContext


class AplicarInteresesCommand(ServiceDto):
    context: MutationAuditContext
    fecha_corte: date | None = None  # por defecto hoy


class InteresAplicadoRead(ServiceDto):
    persona_id: int
    persona_nombre: str
    meses: int
    saldo_base: float
    interes: float
    movimiento_id: int


class AplicarInteresesResult(ServiceDto):
    aplicados: list[InteresAplicadoRead]
