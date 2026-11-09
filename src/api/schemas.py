"""Esquemas wire (JSON) del contrato HTTP. Distintos de los DTOs de servicio.

Montos: en respuestas son ``float`` en pesos; en bodies de entrada ``Decimal`` (2 decimales).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.api import wire_enums


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ─── Genéricos ────────────────────────────────────────────────────────────────


class Health(WireModel):
    status: str = "ok"


class Deleted(WireModel):
    deleted: bool = True


class Credenciales(WireModel):
    user_id: int
    username: str
    password_temporal: str


# ─── Auth ─────────────────────────────────────────────────────────────────────


class LoginRequest(WireModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(WireModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class CurrentUser(WireModel):
    id: int
    username: str
    role: wire_enums.Role
    persona_id: int | None = None
    persona_nombre: str | None = None
    debe_cambiar_password: bool


class LoginResult(WireModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user: CurrentUser


# ─── Personas ─────────────────────────────────────────────────────────────────


class Persona(WireModel):
    id: int
    nombre: str
    apellido: str
    nombre_completo: str
    documento: str | None = None
    telefono: str | None = None
    email: str | None = None
    interes_mensual: float
    descripcion: str | None = None
    fecha_inicio: date
    creado_en: datetime
    saldo: float
    num_movimientos: int
    ultimo_movimiento: date | None = None
    username: str | None = None


class CreatePersonaRequest(WireModel):
    nombre: str = Field(min_length=1, max_length=80)
    apellido: str = Field(min_length=1, max_length=80)
    documento: str | None = Field(default=None, max_length=40)
    telefono: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)
    interes_mensual: float = Field(default=0, ge=0, le=1, description="Tasa mensual (0.02 = 2 %)")
    descripcion: str | None = Field(default=None, max_length=500)
    monto_inicial: Decimal = Field(default=Decimal(0), max_digits=15, decimal_places=2)
    crear_usuario: bool = True
    username: str | None = Field(default=None, max_length=60)


class UpdatePersonaRequest(WireModel):
    """PATCH parcial: solo se modifican los campos presentes (``null`` borra los opcionales)."""

    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    apellido: str | None = Field(default=None, min_length=1, max_length=80)
    documento: str | None = Field(default=None, max_length=40)
    telefono: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)
    interes_mensual: float | None = Field(default=None, ge=0, le=1)
    descripcion: str | None = Field(default=None, max_length=500)


class CreatePersonaResult(WireModel):
    persona: Persona
    credenciales: Credenciales | None = None


# ─── Movimientos ──────────────────────────────────────────────────────────────


class Movimiento(WireModel):
    id: int
    persona_id: int
    fecha: date
    monto: float
    tipo: wire_enums.TipoMovimiento
    descripcion: str
    saldo: float | None = None
    creado_en: datetime


class RegistrarMovimientoRequest(WireModel):
    monto: Decimal = Field(
        max_digits=15,
        decimal_places=2,
        description="Positivo aumenta la deuda; negativo es un abono",
    )
    descripcion: str = Field(default="", max_length=500)
    fecha: date | None = Field(default=None, description="Por defecto hoy")
    tipo: wire_enums.TipoMovimientoManual | None = Field(
        default=None, description="Por defecto según el signo del monto"
    )


class AplicarInteresesRequest(WireModel):
    fecha_corte: date | None = None


class InteresAplicado(WireModel):
    persona_id: int
    persona_nombre: str
    meses: int
    saldo_base: float
    interes: float
    movimiento_id: int


class AplicarInteresesResult(WireModel):
    aplicados: list[InteresAplicado]


# ─── Analítica ────────────────────────────────────────────────────────────────


class PuntoSaldo(WireModel):
    fecha: date
    saldo: float


class Mes(WireModel):
    mes: str
    cargos: float
    abonos: float
    neto: float
    saldo_fin: float


class ResumenDeuda(WireModel):
    saldo: float
    total_cargos: float
    total_abonos: float
    total_intereses: float
    total_ajustes: float
    num_movimientos: int
    primer_movimiento: date | None = None
    ultimo_movimiento: date | None = None
    ultimo_abono_fecha: date | None = None
    ultimo_abono_monto: float | None = None
    promedio_abono: float | None = None
    dias_desde_ultimo_abono: int | None = None


class PersonaAnalitica(WireModel):
    persona: Persona
    resumen: ResumenDeuda
    serie_saldo: list[PuntoSaldo]
    mensual: list[Mes]


class MovimientoReciente(Movimiento):
    persona_nombre: str


class Dashboard(WireModel):
    total_por_cobrar: float
    total_a_favor_de_otros: float
    saldo_neto: float
    personas_total: int
    personas_con_deuda: int
    cobrado_ultimos_30d: float
    prestado_ultimos_30d: float
    top_deudores: list[Persona]
    mensual: list[Mes]
    recientes: list[MovimientoReciente]


# ─── Usuarios ─────────────────────────────────────────────────────────────────


class UserAccount(WireModel):
    id: int
    username: str
    role: wire_enums.Role
    persona_id: int | None = None
    persona_nombre: str | None = None
    activo: bool
    debe_cambiar_password: bool
    bloqueado: bool
    ultimo_login: datetime | None = None
    creado_en: datetime


class CreateUserRequest(WireModel):
    username: str = Field(min_length=3, max_length=60)
    role: wire_enums.Role
    persona_id: int | None = Field(default=None, description="Obligatorio para rol 'usuario'")


class UpdateUserRequest(WireModel):
    username: str | None = Field(default=None, min_length=3, max_length=60)
    activo: bool | None = None
