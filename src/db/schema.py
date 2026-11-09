"""Esquema SQLite versionado con ``PRAGMA user_version``."""

from __future__ import annotations

import sqlite3

MIGRATIONS: list[str] = [
    # v1
    """
    CREATE TABLE personas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT NOT NULL COLLATE NOCASE,
        apellido        TEXT NOT NULL COLLATE NOCASE,
        documento       TEXT,
        telefono        TEXT,
        email           TEXT,
        interes_mensual REAL NOT NULL DEFAULT 0 CHECK (interes_mensual >= 0 AND interes_mensual <= 1),
        descripcion     TEXT,
        fecha_inicio    TEXT NOT NULL,
        creado_en       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
        UNIQUE (nombre, apellido)
    );

    CREATE TABLE users (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        username              TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash         TEXT NOT NULL,
        role                  TEXT NOT NULL CHECK (role IN ('admin', 'usuario')),
        persona_id            INTEGER UNIQUE REFERENCES personas(id) ON DELETE CASCADE,
        activo                INTEGER NOT NULL DEFAULT 1,
        debe_cambiar_password INTEGER NOT NULL DEFAULT 1,
        token_version         INTEGER NOT NULL DEFAULT 0,
        intentos_fallidos     INTEGER NOT NULL DEFAULT 0,
        bloqueado_hasta       TEXT,
        ultimo_login          TEXT,
        creado_en             TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
        CHECK (role = 'admin' OR persona_id IS NOT NULL)
    );

    CREATE TABLE movimientos (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        persona_id     INTEGER NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
        fecha          TEXT NOT NULL,
        monto_centavos INTEGER NOT NULL,
        tipo           TEXT NOT NULL CHECK (tipo IN ('cargo', 'abono', 'interes', 'ajuste')),
        descripcion    TEXT NOT NULL DEFAULT '',
        creado_en      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
        creado_por     INTEGER REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE INDEX ix_movimientos_persona_fecha ON movimientos (persona_id, fecha, id);
    """,
]


def migrate(conn: sqlite3.Connection) -> int:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version, script in enumerate(MIGRATIONS[current:], start=current + 1):
        with conn:
            conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;")
    return len(MIGRATIONS)
