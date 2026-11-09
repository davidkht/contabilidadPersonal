"""Cursores opacos basados en offset (suficiente para SQLite y volúmenes pequeños)."""

from __future__ import annotations

import base64

from src.core.exceptions import ValidationFailed


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        prefix, value = raw.split(":", 1)
        offset = int(value)
        if prefix != "o" or offset < 0:
            raise ValueError
        return offset
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValidationFailed("Cursor inválido") from exc
