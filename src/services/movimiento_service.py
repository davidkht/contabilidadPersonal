"""Movimientos (transacciones) e intereses mensuales."""

from __future__ import annotations

from datetime import date

from src.core.exceptions import NotFound, ValidationFailed
from src.core.pagination import decode_cursor, encode_cursor
from src.models.enums import TipoMovimiento
from src.ports.repositories import UnitOfWorkFactory
from src.services._common import (
    clean,
    get_persona_or_404,
    movimiento_read,
    require_admin,
    require_persona_access,
    to_centavos,
    to_pesos,
)
from src.services.dto.movimientos import (
    AplicarInteresesCommand,
    AplicarInteresesResult,
    DeleteMovimientoCommand,
    InteresAplicadoRead,
    ListMovimientosQuery,
    MovimientoPage,
    MovimientoRead,
    RegistrarMovimientoCommand,
)

_MANUAL_TIPOS = {TipoMovimiento.CARGO, TipoMovimiento.ABONO, TipoMovimiento.AJUSTE}


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


class MovimientoService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    def list_movimientos(self, dto: ListMovimientosQuery) -> MovimientoPage:
        require_persona_access(dto.actor, dto.persona_id)
        offset = decode_cursor(dto.cursor)
        with self._uow() as uow:
            get_persona_or_404(uow, dto.persona_id)
            movimientos = uow.movimientos.list_for_persona(dto.persona_id)
        if dto.orden == "desc":
            movimientos.reverse()
        page = movimientos[offset : offset + dto.limit]
        has_more = offset + dto.limit < len(movimientos)
        return MovimientoPage(
            items=[movimiento_read(m) for m in page],
            next_cursor=encode_cursor(offset + dto.limit) if has_more else None,
            total=len(movimientos),
        )

    def registrar(self, dto: RegistrarMovimientoCommand) -> MovimientoRead:
        require_admin(dto.context)
        req = dto.request
        monto = to_centavos(req.monto)
        if monto == 0:
            raise ValidationFailed("El monto no puede ser cero")
        if req.tipo is None:
            tipo = TipoMovimiento.from_amount(monto)
        else:
            try:
                tipo = TipoMovimiento(req.tipo)
            except ValueError as exc:
                raise ValidationFailed("Tipo de movimiento inválido") from exc
            if tipo not in _MANUAL_TIPOS:
                raise ValidationFailed("Los intereses se generan con la acción de intereses")
            if (
                tipo is TipoMovimiento.CARGO
                and monto < 0
                or tipo is TipoMovimiento.ABONO
                and monto > 0
            ):
                raise ValidationFailed("Un cargo debe ser positivo y un abono negativo")
        fecha = req.fecha or date.today()
        if fecha > date.today():
            raise ValidationFailed("La fecha no puede ser futura")
        with self._uow() as uow:
            get_persona_or_404(uow, dto.persona_id)
            mov_id = uow.movimientos.add(
                persona_id=dto.persona_id,
                fecha=fecha,
                monto_centavos=monto,
                tipo=tipo,
                descripcion=clean(req.descripcion) or "",
                creado_por=dto.context.user_id,
            )
            uow.commit()
            created = next(
                m for m in uow.movimientos.list_for_persona(dto.persona_id) if m.id == mov_id
            )
        return movimiento_read(created)

    def eliminar(self, dto: DeleteMovimientoCommand) -> None:
        require_admin(dto.context)
        with self._uow() as uow:
            mov = uow.movimientos.get(dto.movimiento_id)
            if mov is None or mov.persona_id != dto.persona_id:
                raise NotFound("Movimiento no encontrado")
            uow.movimientos.delete(mov.id)
            uow.commit()

    def aplicar_intereses(self, dto: AplicarInteresesCommand) -> AplicarInteresesResult:
        """Port de ``verificar_y_calcular_intereses`` de la app original.

        Para cada persona con interés > 0 y saldo positivo: si han pasado ≥ 30 días desde su último
        movimiento, se cobra ``saldo × tasa × meses`` (meses de calendario transcurridos). Como el
        cargo crea un movimiento nuevo, volver a ejecutar la acción el mismo día no duplica nada.
        """
        require_admin(dto.context)
        corte = dto.fecha_corte or date.today()
        aplicados: list[InteresAplicadoRead] = []
        with self._uow() as uow:
            for persona in uow.personas.list_all():
                if persona.interes_mensual <= 0 or persona.saldo_centavos <= 0:
                    continue
                if persona.ultimo_movimiento is None:
                    continue
                if (corte - persona.ultimo_movimiento).days < 30:
                    continue
                meses = _months_between(persona.ultimo_movimiento, corte)
                if meses <= 0:
                    continue
                interes = to_centavos(
                    to_pesos(persona.saldo_centavos) * persona.interes_mensual * meses
                )
                if interes <= 0:
                    continue
                mov_id = uow.movimientos.add(
                    persona_id=persona.id,
                    fecha=corte,
                    monto_centavos=interes,
                    tipo=TipoMovimiento.INTERES,
                    descripcion=f"Interés acumulado ({meses} mes{'es' if meses > 1 else ''})",
                    creado_por=dto.context.user_id,
                )
                aplicados.append(
                    InteresAplicadoRead(
                        persona_id=persona.id,
                        persona_nombre=persona.nombre_completo,
                        meses=meses,
                        saldo_base=to_pesos(persona.saldo_centavos),
                        interes=to_pesos(interes),
                        movimiento_id=mov_id,
                    )
                )
            uow.commit()
        return AplicarInteresesResult(aplicados=aplicados)
