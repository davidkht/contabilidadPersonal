"""Arranque idempotente: migraciones, importación legacy y cuentas iniciales."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from src.bootstrap.legacy_import import import_legacy
from src.core.config import Settings
from src.core.security import generate_password, hash_password
from src.db.connection import Database
from src.models.enums import Role
from src.ports.repositories import UnitOfWork
from src.services._common import slugify, unique_username, validate_username

log = logging.getLogger(__name__)


def _append_credentials(path: Path, title: str, rows: list[tuple[str, str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", encoding="utf-8") as fh:
        if new:
            fh.write(
                "# Credenciales iniciales generadas automáticamente.\n"
                "# Entrégalas a cada persona; el sistema pedirá cambiarlas en el primer ingreso.\n"
                "# BORRA ESTE ARCHIVO cuando ya las hayas repartido.\n"
            )
        fh.write(f"\n## {title} — {datetime.now(UTC):%Y-%m-%d %H:%M UTC}\n")
        fh.write(f"{'usuario':<28} {'contraseña':<16} {'rol':<8} persona\n")
        for username, password, role, persona in rows:
            fh.write(f"{username:<28} {password:<16} {role:<8} {persona}\n")
    path.chmod(0o600)


def _create_users_for_personas(uow: UnitOfWork, persona_ids: list[int]) -> list[tuple]:
    rows = []
    for pid in persona_ids:
        persona = uow.personas.get(pid)
        if persona is None or uow.users.get_by_persona(pid):
            continue
        username = unique_username(uow, slugify(persona.nombre, persona.apellido))
        password = generate_password()
        uow.users.add(
            username=username,
            password_hash=hash_password(password),
            role=Role.USUARIO,
            persona_id=pid,
            debe_cambiar_password=True,
        )
        rows.append((username, password, "usuario", persona.nombre_completo))
    return rows


def bootstrap(settings: Settings, database: Database) -> None:
    database.initialize()
    with database.unit_of_work() as uow:
        has_personas = bool(uow.personas.list_all())
        rows: list[tuple] = []
        legacy = settings.legacy_db_path
        if not has_personas and legacy and legacy.is_file() and legacy.stat().st_size > 0:
            report = import_legacy(uow, legacy)
            log.info(
                "Importadas %d personas y %d movimientos desde %s",
                report.personas,
                report.movimientos,
                legacy,
            )
            for ajuste in report.ajustes:
                log.warning("Ajuste de migración: %s", ajuste)
            rows += _create_users_for_personas(uow, report.persona_ids)

        if uow.users.count_admins() == 0:
            username = validate_username(settings.admin_username)
            password = settings.admin_password or generate_password(16)
            uow.users.add(
                username=username,
                password_hash=hash_password(password),
                role=Role.ADMIN,
                persona_id=None,
                debe_cambiar_password=settings.admin_password is None,
            )
            shown = password if settings.admin_password is None else "(APP_ADMIN_PASSWORD)"
            rows.insert(0, (username, shown, "admin", "-"))
        uow.commit()

    if rows:
        _append_credentials(settings.credentials_file, "Cuentas creadas", rows)
        log.warning(
            "Se crearon %d cuentas. Credenciales en %s", len(rows), settings.credentials_file
        )
