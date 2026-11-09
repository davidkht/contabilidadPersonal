from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class Persona:
    """Persona con una cuenta de deuda. ``saldo_centavos`` > 0 => me debe; < 0 => le debo."""

    id: int
    nombre: str
    apellido: str
    documento: str | None
    telefono: str | None
    email: str | None
    interes_mensual: float  # fracción mensual: 0.02 = 2 %
    descripcion: str | None
    fecha_inicio: date
    creado_en: datetime
    saldo_centavos: int = 0
    num_movimientos: int = 0
    ultimo_movimiento: date | None = None

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()
