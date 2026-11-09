from __future__ import annotations

import sqlite3
from datetime import date

from src.db._mapping import serialize, to_date, to_datetime
from src.models.persona import Persona

_UPDATABLE = {
    "nombre",
    "apellido",
    "documento",
    "telefono",
    "email",
    "interes_mensual",
    "descripcion",
}

_SELECT = """
SELECT p.*,
       COALESCE(SUM(m.monto_centavos), 0) AS saldo_centavos,
       COUNT(m.id)                        AS num_movimientos,
       MAX(m.fecha)                       AS ultimo_movimiento
FROM personas p
LEFT JOIN movimientos m ON m.persona_id = p.id
"""


def _row_to_persona(row: sqlite3.Row) -> Persona:
    return Persona(
        id=row["id"],
        nombre=row["nombre"],
        apellido=row["apellido"],
        documento=row["documento"],
        telefono=row["telefono"],
        email=row["email"],
        interes_mensual=row["interes_mensual"],
        descripcion=row["descripcion"],
        fecha_inicio=to_date(row["fecha_inicio"]),
        creado_en=to_datetime(row["creado_en"]),
        saldo_centavos=row["saldo_centavos"],
        num_movimientos=row["num_movimientos"],
        ultimo_movimiento=to_date(row["ultimo_movimiento"]),
    )


class SqlitePersonaRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self) -> list[Persona]:
        rows = self._conn.execute(f"{_SELECT} GROUP BY p.id ORDER BY p.nombre, p.apellido")
        return [_row_to_persona(r) for r in rows]

    def get(self, persona_id: int) -> Persona | None:
        row = self._conn.execute(
            f"{_SELECT} WHERE p.id = ? GROUP BY p.id", (persona_id,)
        ).fetchone()
        return _row_to_persona(row) if row else None

    def exists_name(self, nombre: str, apellido: str, *, exclude_id: int | None = None) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM personas WHERE nombre = ? AND apellido = ? AND id IS NOT ?",
            (nombre, apellido, exclude_id),
        ).fetchone()
        return row is not None

    def add(
        self,
        *,
        nombre: str,
        apellido: str,
        documento: str | None,
        telefono: str | None,
        email: str | None,
        interes_mensual: float,
        descripcion: str | None,
        fecha_inicio: date,
    ) -> int:
        cur = self._conn.execute(
            """INSERT INTO personas
               (nombre, apellido, documento, telefono, email, interes_mensual, descripcion,
                fecha_inicio)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                nombre,
                apellido,
                documento,
                telefono,
                email,
                interes_mensual,
                descripcion,
                fecha_inicio.isoformat(),
            ),
        )
        return int(cur.lastrowid)

    def update(self, persona_id: int, fields: dict[str, object]) -> None:
        cols = [k for k in fields if k in _UPDATABLE]
        if not cols:
            return
        assignments = ", ".join(f"{c} = ?" for c in cols)
        self._conn.execute(
            f"UPDATE personas SET {assignments} WHERE id = ?",
            (*[serialize(fields[c]) for c in cols], persona_id),
        )

    def delete(self, persona_id: int) -> None:
        self._conn.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
