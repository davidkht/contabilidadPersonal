"""Factory de la app FastAPI: API bajo ``/api`` + frontend estático opcional en ``/``."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.commons import REQUEST_ID_HEADER, register_exception_handlers
from src.api.middleware import SecurityHeadersMiddleware
from src.api.routes import api_router
from src.bootstrap.seed import bootstrap
from src.core.config import Settings, get_settings
from src.core.dependencies import build_container

log = logging.getLogger(__name__)

DOCS_URL = "/api/docs"
REDOC_URL = "/api/redoc"
OPENAPI_URL = "/api/openapi.json"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    # El container se construye aquí (no al importar el módulo de rutas) y queda disponible en
    # ``app.state`` incluso antes del lifespan; el lifespan solo ejecuta el bootstrap de la DB.
    container = build_container(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        bootstrap(settings, container.database)
        app.state.container = container
        log.info("API lista (env=%s, db=%s)", settings.env, settings.db_path)
        yield

    docs = settings.docs_enabled
    app = FastAPI(
        title="Contabilidad Personal",
        version="2.0.0",
        description="Control de deudas personales.",
        lifespan=lifespan,
        docs_url=DOCS_URL if docs else None,
        redoc_url=REDOC_URL if docs else None,
        openapi_url=OPENAPI_URL if docs else None,
        swagger_ui_oauth2_redirect_url=f"{DOCS_URL}/oauth2-redirect" if docs else None,
    )
    app.state.container = container
    app.state.settings = settings

    register_exception_handlers(app)
    app.include_router(api_router)

    app.add_middleware(
        SecurityHeadersMiddleware,
        csp_exempt_paths=frozenset({DOCS_URL, REDOC_URL}) if docs else frozenset(),
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER],
            max_age=600,
        )

    # Montado al final: las rutas /api tienen prioridad y "/" sirve index.html.
    web_dir = settings.web_dir
    if web_dir is not None and web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app


app = create_app()
