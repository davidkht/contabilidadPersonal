"""Flujos de administración: personas, movimientos, usuarios, dashboard y autorización."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from _support import bearer


@pytest.fixture
def usuario(client, login, crear_persona):
    """Persona 'Ana Pérez' con saldo inicial 1000 y token de su cuenta."""
    created = crear_persona("Ana", "Pérez", monto_inicial=1000, email="ana@example.com")
    cred = created["credenciales"]
    token = login(cred["username"], cred["password_temporal"])
    return {"persona": created["persona"], "cred": cred, "headers": bearer(token)}


def test_usuario_no_accede_a_admin_403(client, usuario):
    for method, path in [
        ("get", "/api/admin/dashboard"),
        ("get", "/api/admin/personas"),
        ("get", f"/api/admin/personas/{usuario['persona']['id']}"),
        ("get", "/api/admin/usuarios"),
        ("post", "/api/admin/intereses/aplicar"),
    ]:
        res = getattr(client, method)(path, headers=usuario["headers"])
        assert res.status_code == 403, (path, res.text)
        body = res.json()
        assert body["success"] is False
        assert body["error"]["code"] == "permission_denied"


def test_usuario_solo_ve_su_propia_deuda(client, usuario, crear_persona):
    otra = crear_persona("Luis", "Gómez", monto_inicial=500)["persona"]
    # Las rutas de otra persona son solo admin.
    res = client.get(f"/api/admin/personas/{otra['id']}/movimientos", headers=usuario["headers"])
    assert res.status_code == 403
    res = client.get(f"/api/admin/personas/{otra['id']}/analitica", headers=usuario["headers"])
    assert res.status_code == 403
    # /api/me solo devuelve lo suyo.
    data = client.get("/api/me/analitica", headers=usuario["headers"]).json()["data"]
    assert data["persona"]["id"] == usuario["persona"]["id"]
    movs = client.get("/api/me/movimientos", headers=usuario["headers"]).json()["data"]
    assert {m["persona_id"] for m in movs} == {usuario["persona"]["id"]}


def test_flujo_admin_crea_persona_y_usuario_ve_su_saldo(client, admin_headers, usuario):
    persona = usuario["persona"]
    assert persona["saldo"] == 1000.0
    assert persona["nombre_completo"] == "Ana Pérez"
    assert usuario["cred"]["username"]
    assert usuario["cred"]["password_temporal"]

    res = client.get("/api/me/analitica", headers=usuario["headers"])
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["resumen"]["saldo"] == 1000.0
    assert data["persona"]["saldo"] == 1000.0
    assert len(data["mensual"]) == 12

    res = client.get("/api/me/analitica?meses=3", headers=usuario["headers"])
    assert len(res.json()["data"]["mensual"]) == 3

    res = client.get("/api/me/movimientos", headers=usuario["headers"])
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["page"]["total"] == 1
    assert body["data"][0]["monto"] == 1000.0
    assert body["data"][0]["tipo"] in {"cargo", "ajuste"}


def test_crear_persona_sin_usuario_credenciales_null(client, admin_headers):
    res = client.post(
        "/api/admin/personas",
        json={"nombre": "Sin", "apellido": "Cuenta", "crear_usuario": False},
        headers=admin_headers,
    )
    assert res.status_code == 201, res.text
    data = res.json()["data"]
    assert data["credenciales"] is None
    assert data["persona"]["username"] is None


def test_crear_persona_duplicada_409(client, admin_headers, crear_persona):
    crear_persona("Ana", "Pérez")
    res = client.post(
        "/api/admin/personas", json={"nombre": "Ana", "apellido": "Pérez"}, headers=admin_headers
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"


def test_admin_sin_persona_me_404(client, admin_headers):
    res = client.get("/api/me/analitica", headers=admin_headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"
    res = client.get("/api/me/movimientos", headers=admin_headers)
    assert res.status_code == 404
    assert res.json()["success"] is False


def test_registrar_y_borrar_movimiento(client, admin_headers, usuario):
    pid = usuario["persona"]["id"]
    res = client.post(
        f"/api/admin/personas/{pid}/movimientos",
        json={"monto": -250.5, "descripcion": "Pago parcial"},
        headers=admin_headers,
    )
    assert res.status_code == 201, res.text
    mov = res.json()["data"]
    assert mov["tipo"] == "abono"
    assert mov["monto"] == -250.5
    assert mov["fecha"] == date.today().isoformat()

    persona = client.get(f"/api/admin/personas/{pid}", headers=admin_headers).json()["data"]
    assert persona["saldo"] == 749.5
    me = client.get("/api/me/analitica", headers=usuario["headers"]).json()["data"]
    assert me["resumen"]["saldo"] == 749.5
    assert me["resumen"]["ultimo_abono_monto"] == 250.5

    res = client.get(f"/api/admin/personas/{pid}/movimientos?orden=asc", headers=admin_headers)
    body = res.json()
    assert body["meta"]["page"]["total"] == 2
    assert [m["monto"] for m in body["data"]] == [1000.0, -250.5]

    res = client.delete(f"/api/admin/personas/{pid}/movimientos/{mov['id']}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["data"] == {"deleted": True}
    persona = client.get(f"/api/admin/personas/{pid}", headers=admin_headers).json()["data"]
    assert persona["saldo"] == 1000.0

    res = client.delete(f"/api/admin/personas/{pid}/movimientos/{mov['id']}", headers=admin_headers)
    assert res.status_code == 404


def test_movimiento_ajuste_y_validaciones(client, admin_headers, usuario):
    pid = usuario["persona"]["id"]
    url = f"/api/admin/personas/{pid}/movimientos"
    res = client.post(url, json={"monto": -10, "tipo": "ajuste"}, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["data"]["tipo"] == "ajuste"
    # interés no se registra a mano (rechazado por el wire enum)
    res = client.post(url, json={"monto": 10, "tipo": "interes"}, headers=admin_headers)
    assert res.status_code == 422
    # cargo negativo -> regla de negocio
    res = client.post(url, json={"monto": -10, "tipo": "cargo"}, headers=admin_headers)
    assert res.status_code == 422
    # fecha futura
    manana = (date.today() + timedelta(days=1)).isoformat()
    res = client.post(url, json={"monto": 10, "fecha": manana}, headers=admin_headers)
    assert res.status_code == 422
    # más de 2 decimales
    res = client.post(url, json={"monto": 10.123}, headers=admin_headers)
    assert res.status_code == 422


def test_paginacion_movimientos(client, admin_headers, usuario):
    pid = usuario["persona"]["id"]
    for monto in (1, 2, 3):
        client.post(
            f"/api/admin/personas/{pid}/movimientos", json={"monto": monto}, headers=admin_headers
        )
    res = client.get(f"/api/admin/personas/{pid}/movimientos?limit=3", headers=admin_headers)
    body = res.json()
    assert len(body["data"]) == 3
    assert body["meta"]["page"] == {
        "limit": 3,
        "next_cursor": body["meta"]["page"]["next_cursor"],
        "total": 4,
    }
    cursor = body["meta"]["page"]["next_cursor"]
    assert cursor
    res = client.get(
        f"/api/admin/personas/{pid}/movimientos?limit=3&cursor={cursor}", headers=admin_headers
    )
    body = res.json()
    assert len(body["data"]) == 1
    assert "next_cursor" not in body["meta"]["page"]
    res = client.get(
        f"/api/admin/personas/{pid}/movimientos?cursor=basura!!", headers=admin_headers
    )
    assert res.status_code == 422


def test_patch_persona_null_borra_email(client, admin_headers, usuario):
    pid = usuario["persona"]["id"]
    assert usuario["persona"]["email"] == "ana@example.com"
    res = client.patch(
        f"/api/admin/personas/{pid}",
        json={"email": None, "telefono": "3001234567"},
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data.get("email") is None
    assert data["telefono"] == "3001234567"
    assert data["nombre"] == "Ana"  # campos no enviados no cambian

    res = client.patch(
        f"/api/admin/personas/{pid}", json={"nombre": "Ana María"}, headers=admin_headers
    )
    assert res.json()["data"]["nombre_completo"] == "Ana María Pérez"
    assert res.json()["data"]["telefono"] == "3001234567"

    res = client.patch(
        f"/api/admin/personas/{pid}", json={"monto_inicial": 5}, headers=admin_headers
    )
    assert res.status_code == 422


def test_listar_y_buscar_personas(client, admin_headers, crear_persona):
    crear_persona("Ana", "Pérez", monto_inicial=100)
    crear_persona("Luis", "Gómez")
    res = client.get("/api/admin/personas", headers=admin_headers)
    assert {p["nombre_completo"] for p in res.json()["data"]} == {"Ana Pérez", "Luis Gómez"}
    res = client.get("/api/admin/personas?buscar=luis", headers=admin_headers)
    assert [p["nombre"] for p in res.json()["data"]] == ["Luis"]
    res = client.get("/api/admin/personas?solo_con_saldo=true", headers=admin_headers)
    assert [p["nombre"] for p in res.json()["data"]] == ["Ana"]


def test_borrar_persona(client, admin_headers, usuario):
    pid = usuario["persona"]["id"]
    res = client.delete(f"/api/admin/personas/{pid}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["data"] == {"deleted": True}
    assert client.get(f"/api/admin/personas/{pid}", headers=admin_headers).status_code == 404
    # su cuenta desaparece con ella
    assert client.get("/api/auth/me", headers=usuario["headers"]).status_code == 401


def test_analitica_de_persona_admin(client, admin_headers, usuario):
    pid = usuario["persona"]["id"]
    res = client.get(f"/api/admin/personas/{pid}/analitica?meses=6", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["resumen"]["saldo"] == 1000.0
    assert len(data["mensual"]) == 6
    assert (
        client.get("/api/admin/personas/9999/analitica", headers=admin_headers).status_code == 404
    )


def test_dashboard(client, admin_headers, usuario, crear_persona):
    crear_persona("Luis", "Gómez", monto_inicial=-200, crear_usuario=False)
    res = client.get("/api/admin/dashboard?meses=6&top=1&recientes=5", headers=admin_headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["total_por_cobrar"] == 1000.0
    assert data["total_a_favor_de_otros"] == 200.0
    assert data["saldo_neto"] == 800.0
    assert data["personas_total"] == 2
    assert len(data["mensual"]) == 6
    assert len(data["top_deudores"]) == 1
    assert data["top_deudores"][0]["nombre"] == "Ana"
    assert {m["persona_nombre"] for m in data["recientes"]} == {"Ana Pérez", "Luis Gómez"}


def test_aplicar_intereses(client, admin_headers, crear_persona):
    hace_dos_meses = (date.today() - timedelta(days=65)).isoformat()
    pid = crear_persona("Ana", "Pérez", interes_mensual=0.02, crear_usuario=False)["persona"]["id"]
    client.post(
        f"/api/admin/personas/{pid}/movimientos",
        json={"monto": 1000, "fecha": hace_dos_meses},
        headers=admin_headers,
    )
    res = client.post("/api/admin/intereses/aplicar", headers=admin_headers)
    assert res.status_code == 200, res.text
    aplicados = res.json()["data"]["aplicados"]
    assert len(aplicados) == 1
    assert aplicados[0]["persona_id"] == pid
    assert aplicados[0]["interes"] > 0
    # Segunda vez el mismo día: nada que aplicar. Con body explícito también funciona.
    res = client.post(
        "/api/admin/intereses/aplicar",
        json={"fecha_corte": date.today().isoformat()},
        headers=admin_headers,
    )
    assert res.json()["data"]["aplicados"] == []


def test_usuarios_crud(client, admin_headers, crear_persona):
    pid = crear_persona("Luis", "Gómez", crear_usuario=False)["persona"]["id"]
    res = client.post(
        "/api/admin/usuarios",
        json={"username": "luis.gomez", "role": "usuario", "persona_id": pid},
        headers=admin_headers,
    )
    assert res.status_code == 201, res.text
    cred = res.json()["data"]
    assert cred["username"] == "luis.gomez"
    assert cred["password_temporal"]

    res = client.post(
        "/api/admin/usuarios", json={"username": "otro", "role": "usuario"}, headers=admin_headers
    )
    assert res.status_code == 422  # rol usuario sin persona
    res = client.post(
        "/api/admin/usuarios", json={"username": "x", "role": "root"}, headers=admin_headers
    )
    assert res.status_code == 422

    res = client.get("/api/admin/usuarios", headers=admin_headers)
    users = {u["username"]: u for u in res.json()["data"]}
    assert users["admin"]["role"] == "admin"
    assert users["luis.gomez"]["persona_id"] == pid
    assert users["luis.gomez"]["debe_cambiar_password"] is True

    res = client.patch(
        f"/api/admin/usuarios/{cred['user_id']}", json={"username": "luisg"}, headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json()["data"]["username"] == "luisg"


def test_admin_no_puede_desactivarse(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json()["data"]
    res = client.patch(
        f"/api/admin/usuarios/{me['id']}", json={"activo": False}, headers=admin_headers
    )
    assert res.status_code == 422
