from __future__ import annotations

import shutil
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.bootstrap.seed import bootstrap
from src.core.config import Settings
from src.core.dependencies import build_container
from src.core.exceptions import NotFound, PermissionDenied, ValidationFailed
from src.services.dto.analytics import PersonaAnaliticaQuery
from src.services.dto.commons import ActorContext, MutationAuditContext
from src.services.dto.movimientos import (
    AplicarInteresesCommand,
    ListMovimientosQuery,
    RegistrarMovimientoCommand,
    RegistrarMovimientoRequest,
)
from src.services.dto.personas import CreatePersonaCommand, CreatePersonaRequest, ListPersonasQuery

ADMIN = MutationAuditContext(user_id=1, role="admin")
LEGACY_DB = Path(__file__).resolve().parents[2] / "databases" / "deudas.db"


@pytest.fixture
def container(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        legacy_db_path=None,
        web_dir=None,
        jwt_secret="s" * 40,
        admin_password="AdminPass123!",
    )
    c = build_container(settings)
    bootstrap(settings, c.database)
    return c


def _crear(c, monto=100_000, interes=0.0, nombre="Ana"):
    return c.personas.create_persona(
        CreatePersonaCommand(
            request=CreatePersonaRequest(
                nombre=nombre,
                apellido="Pérez",
                monto_inicial=Decimal(monto),
                interes_mensual=interes,
            ),
            context=ADMIN,
        )
    )


def test_crear_persona_genera_usuario_y_saldo(container):
    res = _crear(container)
    assert res.persona.saldo == 100_000
    assert res.credenciales.username == "ana.perez"
    assert len(res.credenciales.password_temporal) >= 12


def test_usuario_solo_ve_su_persona(container):
    a = _crear(container, nombre="Ana")
    b = _crear(container, nombre="Beto")
    actor = ActorContext(user_id=a.credenciales.user_id, role="usuario", persona_id=a.persona.id)
    page = container.movimientos.list_movimientos(
        ListMovimientosQuery(actor=actor, persona_id=a.persona.id)
    )
    assert page.total == 1
    with pytest.raises(NotFound):
        container.analytics.persona_analitica(
            PersonaAnaliticaQuery(actor=actor, persona_id=b.persona.id)
        )
    with pytest.raises(PermissionDenied):
        container.personas.list_personas(ListPersonasQuery(actor=actor))


def test_movimiento_valida_signo_y_fecha(container):
    p = _crear(container).persona
    reg = container.movimientos.registrar
    with pytest.raises(ValidationFailed):
        reg(
            RegistrarMovimientoCommand(
                persona_id=p.id,
                context=ADMIN,
                request=RegistrarMovimientoRequest(monto=Decimal(5), tipo="abono"),
            )
        )
    with pytest.raises(ValidationFailed):
        reg(
            RegistrarMovimientoCommand(
                persona_id=p.id,
                context=ADMIN,
                request=RegistrarMovimientoRequest(
                    monto=Decimal(5), fecha=date.today() + timedelta(days=1)
                ),
            )
        )
    mov = reg(
        RegistrarMovimientoCommand(
            persona_id=p.id,
            context=ADMIN,
            request=RegistrarMovimientoRequest(monto=Decimal("-40000.50")),
        )
    )
    assert mov.tipo == "abono" and mov.saldo == 59_999.5


def test_intereses_mensuales_e_idempotencia(container):
    p = _crear(container, monto=100_000, interes=0.02).persona
    corte = date.today() + timedelta(days=65)  # ~2 meses sin movimientos
    res = container.movimientos.aplicar_intereses(
        AplicarInteresesCommand(context=ADMIN, fecha_corte=corte)
    )
    assert len(res.aplicados) == 1
    meses = res.aplicados[0].meses
    assert res.aplicados[0].interes == pytest.approx(100_000 * 0.02 * meses)
    again = container.movimientos.aplicar_intereses(
        AplicarInteresesCommand(context=ADMIN, fecha_corte=corte)
    )
    assert again.aplicados == []
    a = container.analytics.persona_analitica(PersonaAnaliticaQuery(actor=ADMIN, persona_id=p.id))
    assert a.resumen.total_intereses == res.aplicados[0].interes


@pytest.mark.skipif(not LEGACY_DB.exists(), reason="sin base de datos legacy")
def test_importacion_legacy_cuadra_saldos(tmp_path):
    import sqlite3

    legacy = tmp_path / "legacy.db"
    shutil.copy(LEGACY_DB, legacy)
    settings = Settings(
        data_dir=tmp_path / "data", legacy_db_path=legacy, web_dir=None, jwt_secret="s" * 40
    )
    c = build_container(settings)
    bootstrap(settings, c.database)
    bootstrap(settings, c.database)  # idempotente

    src = sqlite3.connect(legacy)
    esperado = {
        (n.strip(), a.strip()): m
        for n, a, m in src.execute("SELECT nombre, apellido, monto FROM Deudas")
    }
    personas = c.personas.list_personas(ListPersonasQuery(actor=ADMIN))
    assert len(personas) == len(esperado)
    for p in personas:
        assert p.saldo == pytest.approx(esperado[(p.nombre, p.apellido)]), p.nombre_completo
        assert p.username
    creds = settings.credentials_file.read_text()
    assert creds.count("usuario ") >= len(esperado)


def test_bloqueo_es_por_ip_y_no_afecta_a_otras_ips(container):
    from src.core.exceptions import AccountLocked, AuthenticationFailed
    from src.services.dto.auth import LoginCommand

    login = container.auth.login
    for _ in range(5):
        with pytest.raises(AuthenticationFailed):
            login(LoginCommand(username="admin", password="mala-1234", ip_address="10.0.0.66"))
    with pytest.raises(AccountLocked):
        login(LoginCommand(username="admin", password="AdminPass123!", ip_address="10.0.0.66"))
    # El dueño legítimo, desde otra IP, sigue pudiendo entrar
    assert login(
        LoginCommand(username="admin", password="AdminPass123!", ip_address="10.0.0.2")
    ).access_token
