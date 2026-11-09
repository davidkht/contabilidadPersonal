"""Enums del contrato HTTP (propios de la capa API; sus valores coinciden con los del dominio)."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    USUARIO = "usuario"


class TipoMovimiento(StrEnum):
    CARGO = "cargo"
    ABONO = "abono"
    INTERES = "interes"
    AJUSTE = "ajuste"


class TipoMovimientoManual(StrEnum):
    """Tipos que un admin puede registrar a mano (los intereses los genera el sistema)."""

    CARGO = "cargo"
    ABONO = "abono"
    AJUSTE = "ajuste"


class Orden(StrEnum):
    ASC = "asc"
    DESC = "desc"
