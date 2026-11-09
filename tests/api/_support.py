"""Utilidades compartidas por los tests de la API (importables desde los módulos de test)."""

from __future__ import annotations

from pathlib import Path

from src.core.config import Settings

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "AdminPass123!"
JWT_SECRET = "x" * 40


def make_settings(data_dir: Path, **overrides) -> Settings:
    values = {
        "env": "dev",
        "data_dir": data_dir,
        "legacy_db_path": None,
        "web_dir": None,
        "jwt_secret": JWT_SECRET,
        "admin_username": ADMIN_USERNAME,
        "admin_password": ADMIN_PASSWORD,
        "cors_origins": [],
    }
    values.update(overrides)
    return Settings(**values)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
