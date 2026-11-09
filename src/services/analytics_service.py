"""Analítica básica de deudas (por persona y global)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from src.core.exceptions import NotFound
from src.models.enums import TipoMovimiento
from src.models.movimiento import Movimiento
from src.ports.repositories import UnitOfWorkFactory
from src.services._common import (
    get_persona_or_404,
    movimiento_read,
    persona_read,
    require_admin,
    require_persona_access,
    to_pesos,
)
from src.services.dto.analytics import (
    DashboardQuery,
    DashboardRead,
    MesRead,
    MiAnaliticaQuery,
    MovimientoRecienteRead,
    PersonaAnaliticaQuery,
    PersonaAnaliticaRead,
    PuntoSaldoRead,
    ResumenDeudaRead,
)


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _last_months(today: date, n: int) -> list[str]:
    keys, y, m = [], today.year, today.month
    for _ in range(n):
        keys.append(f"{y:04d}-{m:02d}")
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return list(reversed(keys))


def _mensual(movs: list[Movimiento], meses: int, today: date) -> list[MesRead]:
    """Cargos/abonos por mes en los últimos ``meses`` meses, con saldo al cierre de cada mes."""
    keys = _last_months(today, meses)
    cargos: dict[str, int] = defaultdict(int)
    abonos: dict[str, int] = defaultdict(int)
    saldo_antes = 0
    for m in movs:
        key = _month_key(m.fecha)
        if key < keys[0]:
            saldo_antes += m.monto_centavos
        elif m.monto_centavos >= 0:
            cargos[key] += m.monto_centavos
        else:
            abonos[key] += -m.monto_centavos
    out, saldo = [], saldo_antes
    for key in keys:
        saldo += cargos[key] - abonos[key]
        out.append(
            MesRead(
                mes=key,
                cargos=to_pesos(cargos[key]),
                abonos=to_pesos(abonos[key]),
                neto=to_pesos(cargos[key] - abonos[key]),
                saldo_fin=to_pesos(saldo),
            )
        )
    return out


def _serie_saldo(movs: list[Movimiento]) -> list[PuntoSaldoRead]:
    """Saldo al cierre de cada día con movimientos (movs en orden cronológico)."""
    by_day: dict[date, int] = {}
    for m in movs:
        by_day[m.fecha] = m.saldo_centavos or 0
    return [PuntoSaldoRead(fecha=d, saldo=to_pesos(s)) for d, s in by_day.items()]


def _resumen(movs: list[Movimiento], saldo: int, today: date) -> ResumenDeudaRead:
    cargos = sum(m.monto_centavos for m in movs if m.tipo is TipoMovimiento.CARGO)
    intereses = sum(m.monto_centavos for m in movs if m.tipo is TipoMovimiento.INTERES)
    ajustes = sum(m.monto_centavos for m in movs if m.tipo is TipoMovimiento.AJUSTE)
    abonos = [m for m in movs if m.tipo is TipoMovimiento.ABONO]
    ultimo_abono = abonos[-1] if abonos else None
    return ResumenDeudaRead(
        saldo=to_pesos(saldo),
        total_cargos=to_pesos(cargos),
        total_abonos=to_pesos(-sum(m.monto_centavos for m in abonos)),
        total_intereses=to_pesos(intereses),
        total_ajustes=to_pesos(ajustes),
        num_movimientos=len(movs),
        primer_movimiento=movs[0].fecha if movs else None,
        ultimo_movimiento=movs[-1].fecha if movs else None,
        ultimo_abono_fecha=ultimo_abono.fecha if ultimo_abono else None,
        ultimo_abono_monto=to_pesos(-ultimo_abono.monto_centavos) if ultimo_abono else None,
        promedio_abono=(
            to_pesos(-sum(m.monto_centavos for m in abonos) // len(abonos)) if abonos else None
        ),
        dias_desde_ultimo_abono=(today - ultimo_abono.fecha).days if ultimo_abono else None,
    )


class AnalyticsService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    def _persona(self, persona_id: int, meses: int) -> PersonaAnaliticaRead:
        today = date.today()
        with self._uow() as uow:
            persona = get_persona_or_404(uow, persona_id)
            user = uow.users.get_by_persona(persona_id)
            movs = uow.movimientos.list_for_persona(persona_id)
        return PersonaAnaliticaRead(
            persona=persona_read(persona, user.username if user else None),
            resumen=_resumen(movs, persona.saldo_centavos, today),
            serie_saldo=_serie_saldo(movs),
            mensual=_mensual(movs, meses, today),
        )

    def persona_analitica(self, dto: PersonaAnaliticaQuery) -> PersonaAnaliticaRead:
        require_persona_access(dto.actor, dto.persona_id)
        return self._persona(dto.persona_id, dto.meses)

    def mi_analitica(self, dto: MiAnaliticaQuery) -> PersonaAnaliticaRead:
        """Analítica de la persona vinculada a la cuenta que hace la petición."""
        if dto.actor.persona_id is None:
            raise NotFound("Tu cuenta no tiene una deuda asociada")
        return self._persona(dto.actor.persona_id, dto.meses)

    def dashboard(self, dto: DashboardQuery) -> DashboardRead:
        require_admin(dto.actor)
        today = date.today()
        hace_30 = today - timedelta(days=30)
        with self._uow() as uow:
            personas = uow.personas.list_all()
            movs = uow.movimientos.list_all()
            usernames = {u.persona_id: u.username for u in uow.users.list_all() if u.persona_id}
        nombres = {p.id: p.nombre_completo for p in personas}
        positivos = sum(p.saldo_centavos for p in personas if p.saldo_centavos > 0)
        negativos = -sum(p.saldo_centavos for p in personas if p.saldo_centavos < 0)
        recientes_30 = [m for m in movs if m.fecha >= hace_30]
        top = sorted((p for p in personas if p.saldo_centavos > 0), key=lambda p: -p.saldo_centavos)
        recientes = sorted(movs, key=lambda m: (m.fecha, m.id), reverse=True)[: dto.recientes]
        return DashboardRead(
            total_por_cobrar=to_pesos(positivos),
            total_a_favor_de_otros=to_pesos(negativos),
            saldo_neto=to_pesos(positivos - negativos),
            personas_total=len(personas),
            personas_con_deuda=sum(1 for p in personas if p.saldo_centavos > 0),
            cobrado_ultimos_30d=to_pesos(
                -sum(m.monto_centavos for m in recientes_30 if m.monto_centavos < 0)
            ),
            prestado_ultimos_30d=to_pesos(
                sum(m.monto_centavos for m in recientes_30 if m.monto_centavos > 0)
            ),
            top_deudores=[persona_read(p, usernames.get(p.id)) for p in top[: dto.top]],
            mensual=_mensual(sorted(movs, key=lambda m: (m.fecha, m.id)), dto.meses, today),
            recientes=[
                MovimientoRecienteRead(
                    **movimiento_read(m).model_dump(), persona_nombre=nombres.get(m.persona_id, "?")
                )
                for m in recientes
            ],
        )
