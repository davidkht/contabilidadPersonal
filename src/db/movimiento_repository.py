from __future__ import annotations

import sqlite3
from datetime import date

from src.db._mapping import to_date, to_datetime
from src.models.enums import TipoMovimiento
from src.models.movimiento import Movimiento

_ORDER = "ORDER BY fecha, id"


def _row(row: sqlite3.Row) -> Movimiento:
    keys = row.keys()
    return Movimiento(
        id=row["id"],
        persona_id=row["persona_id"],
        fecha=to_date(row["fecha"]),
        monto_centavos=row["monto_centavos"],
        tipo=TipoMovimiento(row["tipo"]),
        descripcion=row["descripcion"] or "",
        creado_en=to_datetime(row["creado_en"]),
        creado_por=row["creado_por"],
        saldo_centavos=row["saldo_centavos"] if "saldo_centavos" in keys else None,
    )


class SqliteMovimientoRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_persona(self, persona_id: int) -> list[Movimiento]:
        rows = self._conn.execute(
            f"""SELECT *, SUM(monto_centavos) OVER (
                    PARTITION BY persona_id {_ORDER}
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS saldo_centavos
                FROM movimientos WHERE persona_id = ? {_ORDER}""",
            (persona_id,),
        )
        return [_row(r) for r in rows]

    def list_all(self) -> list[Movimiento]:
        rows = self._conn.execute(
            f"""SELECT *, SUM(monto_centavos) OVER (
                    PARTITION BY persona_id {_ORDER}
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS saldo_centavos
                FROM movimientos {_ORDER}"""
        )
        return [_row(r) for r in rows]

    def get(self, movimiento_id: int) -> Movimiento | None:
        row = self._conn.execute(
            "SELECT * FROM movimientos WHERE id = ?", (movimiento_id,)
        ).fetchone()
        return _row(row) if row else None

    def add(
        self,
        *,
        persona_id: int,
        fecha: date,
        monto_centavos: int,
        tipo: TipoMovimiento,
        descripcion: str,
        creado_por: int | None,
    ) -> int:
        cur = self._conn.execute(
            """INSERT INTO movimientos (persona_id, fecha, monto_centavos, tipo, descripcion,
                                        creado_por)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (persona_id, fecha.isoformat(), monto_centavos, tipo.value, descripcion, creado_por),
        )
        return int(cur.lastrowid)

    def delete(self, movimiento_id: int) -> None:
        self._conn.execute("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))
