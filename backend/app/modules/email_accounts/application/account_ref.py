"""Helpers for email_account_id resolution and stamping."""

from __future__ import annotations

from typing import Any
from uuid import UUID


def _parse_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        return UUID(trimmed)
    return UUID(str(value))


def coalesce_account_id(
    *,
    email_account_id: UUID | str | None = None,
) -> UUID | None:
    """Parse email_account_id."""
    return _parse_uuid(email_account_id)


def resolve_email_account_id(
    payload: dict | None,
    *,
    email_field: str = "email_account_id",
) -> UUID | None:
    """Read email_account_id from payload only."""
    if not payload:
        return None
    return coalesce_account_id(email_account_id=payload.get(email_field))


def stamp_email_account_id(payload: dict, account_id: UUID | None) -> dict:
    """Write email_account_id for persistence."""
    stamped = dict(payload)
    if account_id is None:
        stamped["email_account_id"] = None
    else:
        stamped["email_account_id"] = str(account_id)
    return stamped
