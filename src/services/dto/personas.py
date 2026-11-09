from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from src.services.dto.commons import (
    ActorContext,
    CredencialesRead,
    MutationAuditContext,
    ServiceDto,
)


class PersonaRead(ServiceDto):
    id: int
    nombre: str
    apellido: str
    nombre_completo: str
    documento: str | None
    telefono: str | None
    email: str | None
    interes_mensual: float
    descripcion: str | None
    fecha_inicio: date
    creado_en: datetime
    saldo: float  # pesos; > 0 me debe, < 0 le debo
    num_movimientos: int
    ultimo_movimiento: date | None
    username: str | None = None


class ListPersonasQuery(ServiceDto):
    actor: ActorContext
    buscar: str | None = None
    solo_con_saldo: bool = False


class GetPersonaQuery(ServiceDto):
    actor: ActorContext
    persona_id: int


class CreatePersonaRequest(ServiceDto):
    nombre: str = Field(min_length=1, max_length=80)
    apellido: str = Field(min_length=1, max_length=80)
    documento: str | None = Field(default=None, max_length=40)
    telefono: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)
    interes_mensual: float = Field(default=0, ge=0, le=1)
    descripcion: str | None = Field(default=None, max_length=500)
    monto_inicial: Decimal = Decimal(0)
    crear_usuario: bool = True
    username: str | None = Field(default=None, max_length=60)


class CreatePersonaCommand(ServiceDto):
    request: CreatePersonaRequest
    context: MutationAuditContext


class CreatePersonaResult(ServiceDto):
    persona: PersonaRead
    credenciales: CredencialesRead | None = None


class UpdatePersonaRequest(ServiceDto):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    apellido: str | None = Field(default=None, min_length=1, max_length=80)
    documento: str | None = Field(default=None, max_length=40)
    telefono: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)
    interes_mensual: float | None = Field(default=None, ge=0, le=1)
    descripcion: str | None = Field(default=None, max_length=500)


class UpdatePersonaCommand(ServiceDto):
    persona_id: int
    request: UpdatePersonaRequest
    # Campos presentes explícitamente en el body (permite poner un campo a null).
    fields_set: frozenset[str]
    context: MutationAuditContext


class DeletePersonaCommand(ServiceDto):
    persona_id: int
    context: MutationAuditContext
