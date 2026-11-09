"""Configuración de la aplicación (variables de entorno con prefijo ``APP_``)."""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: Literal["dev", "prod"] = "dev"

    # Persistencia
    data_dir: Path = PROJECT_ROOT / "data"
    db_filename: str = "contabilidad.db"
    # Base de datos de la app antigua. Si existe y la nueva está vacía, se importa al arrancar.
    legacy_db_path: Path | None = PROJECT_ROOT / "databases" / "deudas.db"

    # Frontend estático servido por la misma app (vacío = no servir)
    web_dir: Path | None = PROJECT_ROOT / "web"

    # JWT
    jwt_secret: str | None = Field(default=None, min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "contabilidad-personal"
    access_token_minutes: int = 8 * 60

    # Login
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    min_password_length: int = 10

    # Admin inicial (si no hay ninguno). Sin contraseña -> se genera una aleatoria.
    admin_username: str = "admin"
    admin_password: str | None = None

    # CORS (solo necesario si el frontend se sirve desde otro origen)
    cors_origins: list[str] = []

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_filename

    @property
    def credentials_file(self) -> Path:
        return self.data_dir / "credenciales_iniciales.txt"

    @property
    def docs_enabled(self) -> bool:
        return self.env == "dev"

    def resolved_jwt_secret(self) -> str:
        """Secreto JWT: env en producción; en dev se genera y persiste en ``data/.jwt_secret``."""
        if self.jwt_secret:
            return self.jwt_secret
        if self.env == "prod":
            raise RuntimeError(
                "APP_JWT_SECRET es obligatorio con APP_ENV=prod (mín. 32 caracteres)"
            )
        secret_file = self.data_dir / ".jwt_secret"
        if secret_file.exists():
            return secret_file.read_text().strip()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        value = secrets.token_urlsafe(48)
        secret_file.write_text(value)
        secret_file.chmod(0o600)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
