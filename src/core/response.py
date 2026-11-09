"""Sobre estándar de respuesta: ``{success, data, error, meta}``."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageMeta(BaseModel):
    limit: int
    next_cursor: str | None = None
    total: int | None = None


class ResponseMeta(BaseModel):
    request_id: str | None = None
    page: PageMeta | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel, Generic[T]):  # noqa: UP046 (genérico Pydantic clásico)
    success: bool = True
    data: T | None = None
    error: ErrorBody | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


def paginated(  # noqa: UP047
    items: list[T],
    *,
    next_cursor: str | None,
    limit: int,
    total: int | None = None,
    request_id: str | None = None,
) -> ApiResponse[list[T]]:
    return ApiResponse(
        data=items,
        meta=ResponseMeta(
            request_id=request_id,
            page=PageMeta(limit=limit, next_cursor=next_cursor, total=total),
        ),
    )


def error_response(
    code: str, message: str, *, details: dict | None = None, request_id: str | None = None
) -> dict[str, Any]:
    return ApiResponse[None](
        success=False,
        error=ErrorBody(code=code, message=message, details=details or {}),
        meta=ResponseMeta(request_id=request_id),
    ).model_dump(mode="json")
