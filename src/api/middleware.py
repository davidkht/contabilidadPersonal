"""Middleware ASGI: request id, cabeceras de seguridad y red de seguridad para errores 500."""

from __future__ import annotations

import logging

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.api.commons import REQUEST_ID_HEADER, resolve_request_id, unhandled_error_response

log = logging.getLogger(__name__)

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


class SecurityHeadersMiddleware:
    """Añade ``X-Request-ID`` y cabeceras de seguridad a todas las respuestas HTTP.

    ``csp_exempt_paths``: rutas (p. ej. Swagger UI en dev) que cargan recursos de CDN/inline
    y no pueden vivir bajo la CSP estricta del frontend.
    """

    def __init__(self, app: ASGIApp, *, csp_exempt_paths: frozenset[str] = frozenset()) -> None:
        self.app = app
        self.csp_exempt_paths = csp_exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = resolve_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        scope.setdefault("state", {})["request_id"] = request_id
        path: str = scope.get("path", "")
        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                if path not in self.csp_exempt_paths:
                    headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
                if path == "/api" or path.startswith("/api/"):
                    headers["Cache-Control"] = "no-store"
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log.exception("Error no controlado en %s %s", scope.get("method"), path)
            if started:
                raise
            response = unhandled_error_response(request_id)
            await response(scope, receive, send_wrapper)
