"""Composition root: único lugar donde se conectan puertos con adaptadores."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.config import Settings
from src.core.security import TokenCodec
from src.db.connection import Database
from src.services.analytics_service import AnalyticsService
from src.services.auth_service import AuthService
from src.services.movimiento_service import MovimientoService
from src.services.persona_service import PersonaService
from src.services.user_service import UserService


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    database: Database
    auth: AuthService
    personas: PersonaService
    movimientos: MovimientoService
    users: UserService
    analytics: AnalyticsService


def build_container(settings: Settings) -> Container:
    database = Database(settings.db_path)
    uow = database.unit_of_work
    tokens = TokenCodec(
        settings.resolved_jwt_secret(),
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        ttl_minutes=settings.access_token_minutes,
    )
    return Container(
        settings=settings,
        database=database,
        auth=AuthService(
            uow,
            tokens,
            max_failed_logins=settings.max_failed_logins,
            lockout_minutes=settings.lockout_minutes,
            min_password_length=settings.min_password_length,
        ),
        personas=PersonaService(uow),
        movimientos=MovimientoService(uow),
        users=UserService(uow),
        analytics=AnalyticsService(uow),
    )
