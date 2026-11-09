"""Arranque con la base de datos de la app antigua (``databases/deudas.db``)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from _support import ADMIN_PASSWORD, ADMIN_USERNAME, bearer, make_settings
from fastapi.testclient import TestClient

from src.api.main import create_app

LEGACY_DB = Path(__file__).resolve().parents[2] / "databases" / "deudas.db"


def test_importa_db_legacy(tmp_path):
    if not LEGACY_DB.is_file() or LEGACY_DB.stat().st_size == 0:
        pytest.skip("databases/deudas.db no disponible")
    legacy_copy = tmp_path / "legacy.db"
    shutil.copy2(LEGACY_DB, legacy_copy)

    settings = make_settings(tmp_path / "data", legacy_db_path=legacy_copy)
    with TestClient(create_app(settings)) as client:
        res = client.post(
            "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        headers = bearer(res.json()["data"]["access_token"])
        personas = client.get("/api/admin/personas", headers=headers).json()["data"]
        assert len(personas) == 14
        angel = next(p for p in personas if p["nombre_completo"] == "Angel Yobany")
        assert angel["saldo"] == 3575455.0
        assert angel["username"]  # se le creó cuenta

    # Reiniciar no vuelve a importar (bootstrap idempotente).
    with TestClient(create_app(settings)) as client:
        res = client.post(
            "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        headers = bearer(res.json()["data"]["access_token"])
        assert len(client.get("/api/admin/personas", headers=headers).json()["data"]) == 14
