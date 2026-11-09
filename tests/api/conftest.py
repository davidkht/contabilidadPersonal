"""Fixtures de los tests de la API."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from _support import ADMIN_PASSWORD, ADMIN_USERNAME, bearer, make_settings
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.core.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path / "data")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def login(client: TestClient) -> Callable[[str, str], str]:
    def _login(username: str, password: str) -> str:
        res = client.post("/api/auth/login", json={"username": username, "password": password})
        assert res.status_code == 200, res.text
        return res.json()["data"]["access_token"]

    return _login


@pytest.fixture
def admin_headers(login) -> dict[str, str]:
    return bearer(login(ADMIN_USERNAME, ADMIN_PASSWORD))


@pytest.fixture
def crear_persona(client: TestClient, admin_headers: dict[str, str]):
    """Crea una persona con cuenta y devuelve el ``data`` de la respuesta 201."""

    def _crear(nombre: str = "Ana", apellido: str = "Pérez", **extra) -> dict:
        body = {"nombre": nombre, "apellido": apellido, **extra}
        res = client.post("/api/admin/personas", json=body, headers=admin_headers)
        assert res.status_code == 201, res.text
        return res.json()["data"]

    return _crear
