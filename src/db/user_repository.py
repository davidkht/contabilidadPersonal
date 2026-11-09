from __future__ import annotations

import sqlite3
from datetime import datetime

from src.db._mapping import from_datetime, serialize, to_datetime
from src.models.enums import Role
from src.models.user import User

_UPDATABLE = {
    "username",
    "password_hash",
    "role",
    "activo",
    "debe_cambiar_password",
    "token_version",
    "intentos_fallidos",
    "bloqueado_hasta",
}

_SELECT = """
SELECT u.*, CASE WHEN p.id IS NULL THEN NULL ELSE p.nombre || ' ' || p.apellido END AS persona_nombre
FROM users u LEFT JOIN personas p ON p.id = u.persona_id
"""


def _row(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        role=Role(row["role"]),
        persona_id=row["persona_id"],
        activo=bool(row["activo"]),
        debe_cambiar_password=bool(row["debe_cambiar_password"]),
        token_version=row["token_version"],
        intentos_fallidos=row["intentos_fallidos"],
        bloqueado_hasta=to_datetime(row["bloqueado_hasta"]),
        ultimo_login=to_datetime(row["ultimo_login"]),
        creado_en=to_datetime(row["creado_en"]),
        persona_nombre=row["persona_nombre"],
    )


class SqliteUserRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def _one(self, where: str, params: tuple) -> User | None:
        row = self._conn.execute(f"{_SELECT} WHERE {where}", params).fetchone()
        return _row(row) if row else None

    def list_all(self) -> list[User]:
        return [_row(r) for r in self._conn.execute(f"{_SELECT} ORDER BY u.role, u.username")]

    def get(self, user_id: int) -> User | None:
        return self._one("u.id = ?", (user_id,))

    def get_by_username(self, username: str) -> User | None:
        return self._one("u.username = ?", (username,))

    def get_by_persona(self, persona_id: int) -> User | None:
        return self._one("u.persona_id = ?", (persona_id,))

    def username_taken(self, username: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        return row is not None

    def count_admins(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND activo = 1"
        ).fetchone()[0]

    def add(
        self,
        *,
        username: str,
        password_hash: str,
        role: Role,
        persona_id: int | None,
        debe_cambiar_password: bool,
    ) -> int:
        cur = self._conn.execute(
            """INSERT INTO users (username, password_hash, role, persona_id, debe_cambiar_password)
               VALUES (?, ?, ?, ?, ?)""",
            (username, password_hash, role.value, persona_id, int(debe_cambiar_password)),
        )
        return int(cur.lastrowid)

    def update(self, user_id: int, fields: dict[str, object]) -> None:
        cols = [k for k in fields if k in _UPDATABLE]
        if not cols:
            return
        assignments = ", ".join(f"{c} = ?" for c in cols)
        self._conn.execute(
            f"UPDATE users SET {assignments} WHERE id = ?",
            (*[serialize(fields[c]) for c in cols], user_id),
        )

    def register_failed_login(self, user_id: int, *, lock_until: datetime | None) -> None:
        self._conn.execute(
            """UPDATE users SET intentos_fallidos = intentos_fallidos + 1, bloqueado_hasta = ?
               WHERE id = ?""",
            (from_datetime(lock_until), user_id),
        )

    def register_successful_login(self, user_id: int, at: datetime) -> None:
        self._conn.execute(
            """UPDATE users SET intentos_fallidos = 0, bloqueado_hasta = NULL, ultimo_login = ?
               WHERE id = ?""",
            (from_datetime(at), user_id),
        )
