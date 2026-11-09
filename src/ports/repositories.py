"""Contratos de persistencia que necesitan los servicios."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import date, datetime
from typing import Protocol

from src.models.enums import Role, TipoMovimiento
from src.models.movimiento import Movimiento
from src.models.persona import Persona
from src.models.user import User


class PersonaRepository(Protocol):
    def list_all(self) -> list[Persona]: ...
    def get(self, persona_id: int) -> Persona | None: ...
    def exists_name(self, nombre: str, apellido: str, *, exclude_id: int | None = None) -> bool: ...
    def add(
        self,
        *,
        nombre: str,
        apellido: str,
        documento: str | None,
        telefono: str | None,
        email: str | None,
        interes_mensual: float,
        descripcion: str | None,
        fecha_inicio: date,
    ) -> int: ...
    def update(self, persona_id: int, fields: dict[str, object]) -> None: ...
    def delete(self, persona_id: int) -> None: ...


class MovimientoRepository(Protocol):
    def list_for_persona(self, persona_id: int) -> list[Movimiento]:
        """Todos los movimientos en orden cronológico (fecha, id) con saldo acumulado."""
        ...

    def list_all(self) -> list[Movimiento]: ...
    def get(self, movimiento_id: int) -> Movimiento | None: ...
    def add(
        self,
        *,
        persona_id: int,
        fecha: date,
        monto_centavos: int,
        tipo: TipoMovimiento,
        descripcion: str,
        creado_por: int | None,
    ) -> int: ...
    def delete(self, movimiento_id: int) -> None: ...


class UserRepository(Protocol):
    def list_all(self) -> list[User]: ...
    def get(self, user_id: int) -> User | None: ...
    def get_by_username(self, username: str) -> User | None: ...
    def get_by_persona(self, persona_id: int) -> User | None: ...
    def username_taken(self, username: str) -> bool: ...
    def count_admins(self) -> int: ...
    def add(
        self,
        *,
        username: str,
        password_hash: str,
        role: Role,
        persona_id: int | None,
        debe_cambiar_password: bool,
    ) -> int: ...
    def update(self, user_id: int, fields: dict[str, object]) -> None: ...
    def register_failed_login(self, user_id: int, *, lock_until: datetime | None) -> None: ...
    def register_successful_login(self, user_id: int, at: datetime) -> None: ...


class UnitOfWork(Protocol):
    personas: PersonaRepository
    movimientos: MovimientoRepository
    users: UserRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...


UnitOfWorkFactory = Callable[[], AbstractContextManager[UnitOfWork]]
