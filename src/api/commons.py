"""Utilidades del borde HTTP: contexto de petición, mapeo DTO -> wire y manejo de errores."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.exceptions import DomainError
from src.core.response import error_response

log = logging.getLogger(__name__)


REQUEST_ID_HEADER = "X-Request-ID"
# Solo aceptamos IDs entrantes "seguros" (evita inyección en logs/cabeceras).
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

_HTTP_CODES = {
    400: "bad_request",
    401: "authentication_failed",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "too_many_requests",
}


def resolve_request_id(incoming: str | None) -> str:
    if incoming and _REQUEST_ID_RE.match(incoming):
        return incoming
    return uuid.uuid4().hex


def request_id_of(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    ip_address: str | None
    user_agent: str | None


def get_request_context(request: Request) -> RequestContext:
    request_id = request_id_of(request) or resolve_request_id(
        request.headers.get(REQUEST_ID_HEADER)
    )
    user_agent = request.headers.get("user-agent")
    return RequestContext(
        request_id=request_id,
        ip_address=request.client.host if request.client else None,
        user_agent=user_agent[:300] if user_agent else None,
    )


def wire_response[S: BaseModel](schema_type: type[S], dto: BaseModel) -> S:
    """Construye el esquema wire a partir de un DTO de lectura (vía serialización JSON)."""
    return schema_type.model_validate(dto.model_dump(mode="json"))


def _json_error(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = error_response(code, message, details=details, request_id=request_id_of(request))
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _auth_headers(status_code: int, extra: dict[str, str] | None = None) -> dict[str, str] | None:
    headers = dict(extra or {})
    if status_code == 401:
        headers.setdefault("WWW-Authenticate", "Bearer")
    return headers or None


async def _domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return _json_error(
        request,
        exc.status_code,
        exc.code,
        exc.message,
        exc.details,
        headers=_auth_headers(exc.status_code),
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    status_code = exc.status_code
    if isinstance(exc.detail, str) and exc.detail:
        message = exc.detail
    else:
        try:
            message = HTTPStatus(status_code).phrase
        except ValueError:
            message = "Error"
    code = _HTTP_CODES.get(status_code, "http_error")
    return _json_error(
        request, status_code, code, message, headers=_auth_headers(status_code, exc.headers)
    )


def _clean_validation_errors(errors: Any) -> list[dict[str, Any]]:
    """Quita ``input``/``ctx``/``url`` para no reflejar datos enviados (p. ej. contraseñas)."""
    cleaned = []
    for err in errors:
        cleaned.append(
            {
                "loc": [str(part) for part in err.get("loc", ())],
                "msg": str(err.get("msg", "")),
                "type": str(err.get("type", "")),
            }
        )
    return cleaned


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return _json_error(
        request,
        422,
        "validation_error",
        "Datos de entrada inválidos",
        {"errors": _clean_validation_errors(exc.errors())},
    )


def unhandled_error_response(request_id: str | None) -> JSONResponse:
    body = error_response("internal_error", "Error interno del servidor", request_id=request_id)
    return JSONResponse(status_code=500, content=body)


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Error no controlado en %s %s", request.method, request.url.path, exc_info=exc)
    return unhandled_error_response(request_id_of(request))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
