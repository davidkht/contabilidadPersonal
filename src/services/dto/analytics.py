from __future__ import annotations

from datetime import date

from src.services.dto.commons import ActorContext, ServiceDto
from src.services.dto.movimientos import MovimientoRead
from src.services.dto.personas import PersonaRead


class PuntoSaldoRead(ServiceDto):
    fecha: date
    saldo: float


class MesRead(ServiceDto):
    mes: str  # YYYY-MM
    cargos: float  # suma de aumentos de deuda (incluye intereses)
    abonos: float  # suma de pagos (positivo)
    neto: float
    saldo_fin: float


class ResumenDeudaRead(ServiceDto):
    saldo: float
    total_cargos: float
    total_abonos: float
    total_intereses: float
    total_ajustes: float  # correcciones (saldo = cargos + intereses + ajustes - abonos)
    num_movimientos: int
    primer_movimiento: date | None
    ultimo_movimiento: date | None
    ultimo_abono_fecha: date | None
    ultimo_abono_monto: float | None
    promedio_abono: float | None
    dias_desde_ultimo_abono: int | None


class PersonaAnaliticaQuery(ServiceDto):
    actor: ActorContext
    persona_id: int
    meses: int = 12


class MiAnaliticaQuery(ServiceDto):
    actor: ActorContext
    meses: int = 12


class PersonaAnaliticaRead(ServiceDto):
    persona: PersonaRead
    resumen: ResumenDeudaRead
    serie_saldo: list[PuntoSaldoRead]
    mensual: list[MesRead]


class DashboardQuery(ServiceDto):
    actor: ActorContext
    meses: int = 12
    top: int = 5
    recientes: int = 10


class MovimientoRecienteRead(MovimientoRead):
    persona_nombre: str


class DashboardRead(ServiceDto):
    total_por_cobrar: float  # suma de saldos positivos
    total_a_favor_de_otros: float  # suma de saldos negativos (en positivo)
    saldo_neto: float
    personas_total: int
    personas_con_deuda: int
    cobrado_ultimos_30d: float
    prestado_ultimos_30d: float
    top_deudores: list[PersonaRead]
    mensual: list[MesRead]
    recientes: list[MovimientoRecienteRead]
