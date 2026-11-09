"""Autenticación: login con bloqueo por intentos, JWT revocable y cambio de contraseña."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

import jwt

from src.core.exceptions import AccountLocked, AuthenticationFailed, ValidationFailed
from src.core.security import TokenCodec, hash_password, verify_password
from src.models.user import User
from src.ports.repositories import UnitOfWorkFactory
from src.services._common import validate_new_password
from src.services.dto.auth import (
    ChangePasswordCommand,
    CurrentUserRead,
    GetCurrentUserQuery,
    LoginCommand,
    LoginResult,
    ResolveTokenQuery,
)
from src.services.dto.commons import ActorContext

_INVALID = "Usuario o contraseña incorrectos"
_LOCKED = "Demasiados intentos fallidos. Intenta de nuevo en unos minutos."


class LoginThrottle:
    """Limita intentos fallidos por (IP, usuario) en memoria.

    Evita que alguien bloquee la cuenta de otra persona desde su IP: solo se bloquea a sí mismo.
    El bloqueo de cuenta en la DB queda como red de seguridad contra ataques distribuidos.
    """

    def __init__(self, max_failures: int, window_seconds: float) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._fails: dict[tuple[str, str], list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: tuple[str, str], now: float) -> list[float]:
        items = [t for t in self._fails.get(key, []) if now - t < self._window]
        if items:
            self._fails[key] = items
        else:
            self._fails.pop(key, None)
        return items

    def blocked(self, ip: str | None, username: str) -> bool:
        with self._lock:
            return len(self._recent((ip or "?", username.lower()), time.monotonic())) >= self._max

    def fail(self, ip: str | None, username: str) -> None:
        with self._lock:
            key = (ip or "?", username.lower())
            self._fails[key] = [*self._recent(key, time.monotonic()), time.monotonic()]

    def reset(self, ip: str | None, username: str) -> None:
        with self._lock:
            self._fails.pop((ip or "?", username.lower()), None)


def _current_user(user: User) -> CurrentUserRead:
    return CurrentUserRead(
        id=user.id,
        username=user.username,
        role=user.role.value,
        persona_id=user.persona_id,
        persona_nombre=user.persona_nombre,
        debe_cambiar_password=user.debe_cambiar_password,
    )


class AuthService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        tokens: TokenCodec,
        *,
        max_failed_logins: int,
        lockout_minutes: int,
        min_password_length: int,
        account_lock_threshold: int = 25,
    ) -> None:
        self._uow = uow_factory
        self._tokens = tokens
        self._throttle = LoginThrottle(max_failed_logins, lockout_minutes * 60)
        self._account_threshold = account_lock_threshold
        self._lockout = timedelta(minutes=lockout_minutes)
        self._min_pwd = min_password_length

    def _issue(self, user: User) -> LoginResult:
        token, expires = self._tokens.encode(
            {
                "sub": str(user.id),
                "role": user.role.value,
                "pid": user.persona_id,
                "ver": user.token_version,
            }
        )
        return LoginResult(access_token=token, expires_at=expires, user=_current_user(user))

    def login(self, dto: LoginCommand) -> LoginResult:
        now = datetime.now(UTC)
        username = dto.username.strip()
        if self._throttle.blocked(dto.ip_address, username):
            raise AccountLocked(_LOCKED)
        with self._uow() as uow:
            user = uow.users.get_by_username(username)
            if user is None:
                verify_password(dto.password, None)  # tiempo constante
                self._throttle.fail(dto.ip_address, username)
                raise AuthenticationFailed(_INVALID)
            if user.bloqueado_hasta and user.bloqueado_hasta > now:
                raise AccountLocked(_LOCKED)
            if not verify_password(dto.password, user.password_hash):
                self._throttle.fail(dto.ip_address, username)
                attempts = user.intentos_fallidos + 1
                lock = now + self._lockout if attempts >= self._account_threshold else None
                uow.users.register_failed_login(user.id, lock_until=lock)
                if lock:
                    uow.users.update(user.id, {"intentos_fallidos": 0})
                uow.commit()
                raise AuthenticationFailed(_INVALID)
            if not user.activo:
                raise AuthenticationFailed(_INVALID)
            self._throttle.reset(dto.ip_address, username)
            uow.users.register_successful_login(user.id, now)
            uow.commit()
            return self._issue(user)

    def resolve_token(self, dto: ResolveTokenQuery) -> ActorContext:
        """Valida firma/expiración y que el usuario siga activo con la misma versión de token."""
        try:
            claims = self._tokens.decode(dto.token)
            user_id = int(claims["sub"])
            version = int(claims.get("ver", -1))
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise AuthenticationFailed("Token inválido o expirado") from exc
        with self._uow() as uow:
            user = uow.users.get(user_id)
        if user is None or not user.activo or user.token_version != version:
            raise AuthenticationFailed("Sesión no válida, inicia sesión de nuevo")
        return ActorContext(user_id=user.id, role=user.role.value, persona_id=user.persona_id)

    def get_current_user(self, dto: GetCurrentUserQuery) -> CurrentUserRead:
        with self._uow() as uow:
            user = uow.users.get(dto.actor.user_id)
        if user is None:
            raise AuthenticationFailed("Sesión no válida")
        return _current_user(user)

    def change_password(self, dto: ChangePasswordCommand) -> LoginResult:
        """Cambia la contraseña, invalida los tokens anteriores y emite uno nuevo."""
        with self._uow() as uow:
            user = uow.users.get(dto.context.user_id)
            if user is None:
                raise AuthenticationFailed("Sesión no válida")
            if not verify_password(dto.current_password, user.password_hash):
                raise ValidationFailed("La contraseña actual no es correcta")
            if dto.new_password == dto.current_password:
                raise ValidationFailed("La nueva contraseña debe ser distinta de la actual")
            validate_new_password(
                dto.new_password, min_length=self._min_pwd, username=user.username
            )
            uow.users.update(
                user.id,
                {
                    "password_hash": hash_password(dto.new_password),
                    "debe_cambiar_password": False,
                    "token_version": user.token_version + 1,
                },
            )
            uow.commit()
            refreshed = uow.users.get(user.id)
        return self._issue(refreshed)
