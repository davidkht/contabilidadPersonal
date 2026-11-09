"""Router compuesto de la API (montado bajo ``/api``)."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.routes import admin_dashboard, admin_personas, admin_usuarios, auth, health, me
from src.core.exceptions import NotFound

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(admin_dashboard.router)
api_router.include_router(admin_personas.router)
api_router.include_router(admin_usuarios.router)


@api_router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
def api_not_found(path: str) -> None:
    """Cualquier ``/api/*`` desconocido -> 404 JSON (nunca cae al frontend estático)."""
    raise NotFound("Recurso no encontrado")
