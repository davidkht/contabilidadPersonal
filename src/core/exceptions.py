"""Errores de dominio. La capa HTTP los traduce a códigos de estado."""

from __future__ import annotations


class DomainError(Exception):
    code: str = "domain_error"
    status_code: int = 400

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationFailed(DomainError):
    code = "validation_error"
    status_code = 422


class NotFound(DomainError):
    code = "not_found"
    status_code = 404


class Conflict(DomainError):
    code = "conflict"
    status_code = 409


class AuthenticationFailed(DomainError):
    code = "authentication_failed"
    status_code = 401


class AccountLocked(DomainError):
    code = "account_locked"
    status_code = 429


class PermissionDenied(DomainError):
    code = "permission_denied"
    status_code = 403
