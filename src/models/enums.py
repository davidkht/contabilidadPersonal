from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    USUARIO = "usuario"


class TipoMovimiento(StrEnum):
    CARGO = "cargo"  # aumenta la deuda (préstamo, compra…)
    ABONO = "abono"  # disminuye la deuda (pago)
    INTERES = "interes"  # interés generado automáticamente
    AJUSTE = "ajuste"  # corrección manual / migración

    @classmethod
    def from_amount(cls, monto_centavos: int) -> TipoMovimiento:
        return cls.CARGO if monto_centavos >= 0 else cls.ABONO
