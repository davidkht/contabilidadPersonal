"""Comportamiento transversal de la app: envelope, errores, cabeceras, docs y estáticos."""

from __future__ import annotations

from _support import make_settings
from fastapi.testclient import TestClient

from src.api.deps import get_auth_service
from src.api.main import create_app

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"] == {"status": "ok"}
    assert body["meta"]["request_id"] == res.headers["x-request-id"]


def test_cabeceras_de_seguridad(client):
    res = client.get("/api/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["referrer-policy"] == "no-referrer"
    assert res.headers["content-security-policy"] == CSP
    assert res.headers["cache-control"] == "no-store"


def test_request_id_propagado_y_saneado(client):
    res = client.get("/api/health", headers={"X-Request-ID": "abc-123"})
    assert res.headers["x-request-id"] == "abc-123"
    assert res.json()["meta"]["request_id"] == "abc-123"
    res = client.get("/api/health", headers={"X-Request-ID": "malo id\twith spaces"})
    assert res.headers["x-request-id"] != "malo id\twith spaces"


def test_api_desconocida_404_json(client):
    for method in ("get", "post", "delete"):
        res = getattr(client, method)("/api/no-existe/para-nada")
        assert res.status_code == 404
        assert res.headers["content-type"].startswith("application/json")
        body = res.json()
        assert body["success"] is False
        assert body["error"]["code"] == "not_found"


def test_validacion_422_en_envelope_sin_eco_de_password(client):
    secreto = "ContraseñaSuperSecreta" * 20  # > 200 caracteres
    res = client.post("/api/auth/login", json={"username": "admin", "password": secreto})
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"
    errors = body["error"]["details"]["errors"]
    assert errors and errors[0]["loc"] == ["body", "password"]
    assert "input" not in errors[0]
    assert "SuperSecreta" not in res.text


def test_validacion_campos_extra_y_json_invalido(client):
    res = client.post("/api/auth/login", json={"username": "a", "password": "b", "extra": 1})
    assert res.status_code == 422
    res = client.post(
        "/api/auth/login", content=b"{no json", headers={"Content-Type": "application/json"}
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


def test_metodo_no_permitido_en_envelope(client):
    res = client.delete("/api/auth/login")
    assert res.status_code in (404, 405)
    assert res.json()["success"] is False


def test_error_no_controlado_500_envelope(settings):
    class Roto:
        def login(self, dto):
            raise RuntimeError("detalle interno que no debe salir")

    app = create_app(settings)
    app.dependency_overrides[get_auth_service] = Roto
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "x"},
            headers={"X-Request-ID": "req-500"},
        )
    assert res.status_code == 500
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "internal_error"
    assert body["meta"]["request_id"] == "req-500"
    assert "detalle interno" not in res.text
    assert res.headers["x-request-id"] == "req-500"


def test_docs_solo_en_dev(tmp_path):
    with TestClient(create_app(make_settings(tmp_path / "dev", env="dev"))) as client:
        assert client.get("/api/openapi.json").status_code == 200
        res = client.get("/api/docs")
        assert res.status_code == 200
        assert "content-security-policy" not in res.headers
    with TestClient(create_app(make_settings(tmp_path / "prod", env="prod"))) as client:
        for path in ("/api/docs", "/api/redoc", "/api/openapi.json"):
            res = client.get(path)
            assert res.status_code == 404
            assert res.json()["success"] is False


def test_openapi_contiene_rutas(client):
    paths = client.get("/api/openapi.json").json()["paths"]
    for path in (
        "/api/health",
        "/api/auth/login",
        "/api/auth/me",
        "/api/auth/change-password",
        "/api/me/analitica",
        "/api/me/movimientos",
        "/api/admin/dashboard",
        "/api/admin/personas",
        "/api/admin/personas/{persona_id}",
        "/api/admin/personas/{persona_id}/analitica",
        "/api/admin/personas/{persona_id}/movimientos",
        "/api/admin/personas/{persona_id}/movimientos/{movimiento_id}",
        "/api/admin/intereses/aplicar",
        "/api/admin/usuarios",
        "/api/admin/usuarios/{user_id}",
        "/api/admin/usuarios/{user_id}/reset-password",
    ):
        assert path in paths, path


def test_frontend_estatico(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<!doctype html><title>App</title>", encoding="utf-8")
    (web / "app.js").write_text("console.log(1)", encoding="utf-8")
    with TestClient(create_app(make_settings(tmp_path / "data", web_dir=web))) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert "<title>App</title>" in res.text
        assert res.headers["content-security-policy"] == CSP
        assert "cache-control" not in res.headers or res.headers["cache-control"] != "no-store"
        assert client.get("/app.js").status_code == 200
        assert client.get("/api/health").json()["data"] == {"status": "ok"}
        res = client.get("/api/nada")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "not_found"


def test_cors_solo_si_configurado(tmp_path):
    origin = "http://localhost:5173"
    preflight = {"Origin": origin, "Access-Control-Request-Method": "GET"}
    with TestClient(create_app(make_settings(tmp_path / "a"))) as client:
        res = client.get("/api/health", headers={"Origin": origin})
        assert "access-control-allow-origin" not in res.headers
    settings = make_settings(tmp_path / "b", cors_origins=[origin])
    with TestClient(create_app(settings)) as client:
        res = client.get("/api/health", headers={"Origin": origin})
        assert res.headers["access-control-allow-origin"] == origin
        res = client.options("/api/health", headers=preflight)
        assert res.status_code == 200
