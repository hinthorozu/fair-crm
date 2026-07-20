"""Semicolon-separated multi-email normalization and validation."""

from __future__ import annotations

from email_validator import EmailNotValidError, validate_email


def is_valid_email_address(email: str) -> bool:
    """Return True only for a structurally valid single email address.

    Leading/trailing whitespace must be stripped by the caller before calling.
    Internal whitespace is never accepted (and is never stripped away to "fix" it).
    Uses the project ``email-validator`` dependency with deliverability checks off.
    """
    if not email:
        return False
    # Reject any whitespace so addresses like "abc @.oxom" cannot pass.
    if any(ch.isspace() for ch in email):
        return False
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return False
    return True


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
        # Lowercase for storage only after structural validation of the stripped token.
        # Do not remove internal spaces — invalid tokens raise.
        if not is_valid_email_address(raw):
            raise ValueError(f"Invalid email address: {raw}")
        email = raw.lower()
        if email in seen:
            continue
        seen.add(email)
        normalized.append(email)

    return ";".join(normalized) if normalized else None
