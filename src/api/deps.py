"""Getters de servicios para ``Depends``: resuelven desde el container de la app."""

from __future__ import annotations

from fastapi import Request

from src.services.analytics_service import AnalyticsService
from src.services.auth_service import AuthService
from src.services.movimiento_service import MovimientoService
from src.services.persona_service import PersonaService
from src.services.user_service import UserService


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.container.auth


def get_persona_service(request: Request) -> PersonaService:
    return request.app.state.container.personas


def get_movimiento_service(request: Request) -> MovimientoService:
    return request.app.state.container.movimientos


def get_user_service(request: Request) -> UserService:
    return request.app.state.container.users


def get_analytics_service(request: Request) -> AnalyticsService:
    return request.app.state.container.analytics
