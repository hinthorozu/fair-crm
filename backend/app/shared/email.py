"""Semicolon-separated multi-email normalization and validation."""

from __future__ import annotations


def is_valid_email_address(email: str) -> bool:
    if not email or "@" not in email:
        return False
    if email.startswith("@") or email.endswith("@"):
        return False
    if email.count("@") != 1 or "@@" in email:
        return False
    local, domain = email.rsplit("@", 1)
    return bool(local.strip()) and bool(domain.strip())


def normalize_email_field(value: str | None) -> str | None:
    """Normalize a single or multi-email string to canonical `a@x.com;b@y.com` form."""
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    text = text.replace(",", ";")
    raw_parts = [part.strip() for part in text.split(";")]

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_parts:
        if not raw:
            continue
        email = raw.lower()
        if not is_valid_email_address(email):
            raise ValueError(f"Invalid email address: {raw}")
        if email in seen:
            continue
        seen.add(email)
        normalized.append(email)

    return ";".join(normalized) if normalized else None
