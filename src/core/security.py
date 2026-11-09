"""Primitivas criptográficas: hash de contraseñas (Argon2id) y JWT (HS256)."""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()  # Argon2id
# Hash señuelo para igualar tiempos cuando el usuario no existe.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")

_ALPHABET = string.ascii_letters + string.digits
_AMBIGUOUS = set("Il1O0o")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception:  # noqa: BLE001 — hash corrupto o formato desconocido
        return False


def generate_password(length: int = 14) -> str:
    """Contraseña aleatoria legible (sin caracteres ambiguos), con letras y dígitos."""
    alphabet = [c for c in _ALPHABET if c not in _AMBIGUOUS]
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.isdigit() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
        ):
            return pwd


class TokenCodec:
    def __init__(self, secret: str, *, algorithm: str, issuer: str, ttl_minutes: int) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer
        self.ttl = timedelta(minutes=ttl_minutes)

    def encode(self, claims: dict[str, Any]) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires = now + self.ttl
        payload = {**claims, "iat": now, "nbf": now, "exp": expires, "iss": self._issuer}
        return jwt.encode(payload, self._secret, algorithm=self._algorithm), expires

    def decode(self, token: str) -> dict[str, Any]:
        """Lanza ``jwt.PyJWTError`` si la firma, expiración o emisor no son válidos."""
        return jwt.decode(
            token,
            self._secret,
            algorithms=[self._algorithm],
            issuer=self._issuer,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
