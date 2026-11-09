from __future__ import annotations

from datetime import UTC, date, datetime


def to_date(value: str | None) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def from_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def serialize(value: object) -> object:
    if isinstance(value, datetime):
        return from_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return int(value)
    return value
