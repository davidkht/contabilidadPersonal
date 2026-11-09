"""Conexiones SQLite y unidad de trabajo transaccional."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from src.db.movimiento_repository import SqliteMovimientoRepository
from src.db.persona_repository import SqlitePersonaRepository
from src.db.schema import migrate
from src.db.user_repository import SqliteUserRepository


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


class SqliteUnitOfWork:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.personas = SqlitePersonaRepository(conn)
        self.movimientos = SqliteMovimientoRepository(conn)
        self.users = SqliteUserRepository(conn)
        self._done = False

    def commit(self) -> None:
        self._conn.execute("COMMIT")
        self._done = True

    def rollback(self) -> None:
        if not self._done:
            self._conn.execute("ROLLBACK")
            self._done = True


class Database:
    """Abre una conexión por unidad de trabajo (seguro con hilos del servidor)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        conn = connect(self.path)
        try:
            migrate(conn)
        finally:
            conn.close()

    @contextmanager
    def unit_of_work(self) -> Iterator[SqliteUnitOfWork]:
        conn = connect(self.path)
        conn.execute("BEGIN IMMEDIATE")
        uow = SqliteUnitOfWork(conn)
        try:
            yield uow
            uow.rollback()  # no-op si ya se hizo commit; lecturas terminan aquí
        except BaseException:
            uow.rollback()
            raise
        finally:
            conn.close()
