from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.models.enums import TipoMovimiento


@dataclass(slots=True)
class Movimiento:
    """Transacción firmada: positivo aumenta la deuda, negativo la reduce."""

    id: int
    persona_id: int
    fecha: date
    monto_centavos: int
    tipo: TipoMovimiento
    descripcion: str
    creado_en: datetime
    creado_por: int | None
    saldo_centavos: int | None = None  # saldo acumulado tras este movimiento (calculado)
