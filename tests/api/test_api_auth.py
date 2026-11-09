"""Login, bloqueo, tokens y cambio/restablecimiento de contraseña."""

from __future__ import annotations

import jwt
from _support import ADMIN_PASSWORD, ADMIN_USERNAME, bearer


def test_login_ok_devuelve_token_y_usuario(client):
    res = client.post(
        "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["expires_at"]
    assert data["user"]["username"] == ADMIN_USERNAME
    assert data["user"]["role"] == "admin"
    assert data["user"]["debe_cambiar_password"] is False
    assert body["meta"]["request_id"]


def test_login_credenciales_invalidas_401(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "mala-clave-1"})
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"
    body = res.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "authentication_failed"


def test_login_usuario_inexistente_401(client):
    res = client.post("/api/auth/login", json={"username": "nadie", "password": "x1234567890"})
    assert res.status_code == 401


def test_bloqueo_tras_cinco_fallos_429(client):
    for _ in range(5):
        res = client.post("/api/auth/login", json={"username": "admin", "password": "mala-1234"})
        assert res.status_code == 401
    res = client.post(
        "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert res.status_code == 429
    body = res.json()
    assert body["error"]["code"] == "account_locked"


def test_me_sin_token_401(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"
    assert res.json()["error"]["code"] == "authentication_failed"


def test_token_manipulado_401(client, login):
    token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-2]}{'AA' if signature[-2:] != 'AA' else 'BB'}"
    assert client.get("/api/auth/me", headers=bearer(tampered)).status_code == 401

    forged = jwt.encode(
        {
            "sub": "1",
            "role": "admin",
            "ver": 0,
            "iss": "contabilidad-personal",
            "iat": 1,
            "exp": 4102444800,
        },
        "otro-secreto-" * 4,
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers=bearer(forged)).status_code == 401
    assert client.get("/api/auth/me", headers=bearer("no-es-un-jwt")).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_me_devuelve_usuario_actual(client, admin_headers):
    res = client.get("/api/auth/me", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["username"] == ADMIN_USERNAME
    assert data["role"] == "admin"


def test_change_password_revoca_token_viejo(client, login):
    old = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "NuevaClave2024!"},
        headers=bearer(old),
    )
    assert res.status_code == 200, res.text
    new = res.json()["data"]["access_token"]
    assert new != old

    assert client.get("/api/auth/me", headers=bearer(old)).status_code == 401
    assert client.get("/api/auth/me", headers=bearer(new)).status_code == 200
    # Nueva contraseña funciona, la vieja no.
    assert login(ADMIN_USERNAME, "NuevaClave2024!")
    res = client.post(
        "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert res.status_code == 401


def test_change_password_actual_incorrecta_422(client, admin_headers):
    res = client.post(
        "/api/auth/change-password",
        json={"current_password": "incorrecta-1", "new_password": "NuevaClave2024!"},
        headers=admin_headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


def test_usuario_creado_cambia_password_y_se_quita_la_marca(client, login, crear_persona):
    cred = crear_persona()["credenciales"]
    token = login(cred["username"], cred["password_temporal"])
    me = client.get("/api/auth/me", headers=bearer(token)).json()["data"]
    assert me["debe_cambiar_password"] is True
    assert me["role"] == "usuario"

    res = client.post(
        "/api/auth/change-password",
        json={"current_password": cred["password_temporal"], "new_password": "MiClave-Segura9"},
        headers=bearer(token),
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["user"]["debe_cambiar_password"] is False


def test_reset_password(client, login, admin_headers, crear_persona):
    cred = crear_persona()["credenciales"]
    viejo = login(cred["username"], cred["password_temporal"])

    res = client.post(
        f"/api/admin/usuarios/{cred['user_id']}/reset-password", headers=admin_headers
    )
    assert res.status_code == 200, res.text
    nueva = res.json()["data"]
    assert nueva["user_id"] == cred["user_id"]
    assert nueva["password_temporal"] != cred["password_temporal"]

    res = client.post(
        "/api/auth/login",
        json={"username": cred["username"], "password": cred["password_temporal"]},
    )
    assert res.status_code == 401
    assert login(cred["username"], nueva["password_temporal"])
    # Restablecer la contraseña también debería cerrar las sesiones existentes.
    assert client.get("/api/auth/me", headers=bearer(viejo)).status_code == 401


def test_desactivar_usuario_cierra_su_sesion(client, login, admin_headers, crear_persona):
    cred = crear_persona()["credenciales"]
    token = login(cred["username"], cred["password_temporal"])
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 200

    res = client.patch(
        f"/api/admin/usuarios/{cred['user_id']}", json={"activo": False}, headers=admin_headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["activo"] is False

    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401
    res = client.post(
        "/api/auth/login",
        json={"username": cred["username"], "password": cred["password_temporal"]},
    )
    assert res.status_code == 401
