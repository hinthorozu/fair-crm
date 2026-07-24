"""Semicolon-separated multi-email normalization and validation."""

from __future__ import annotations

from email_validator import EmailNotValidError, validate_email

# Bulk-email recipient addresses only: explicit Turkish letter fold before lowercase.
# Do not map ı. Do not add general Unicode/ASCII transliteration.
_BULK_RECIPIENT_EMAIL_TR_MAP = str.maketrans(
    {
        "Ü": "u",
        "ü": "u",
        "Ş": "s",
        "ş": "s",
        "Ğ": "g",
        "ğ": "g",
        "Ç": "c",
        "ç": "c",
        "Ö": "o",
        "ö": "o",
        "I": "i",
        "İ": "i",
    }
)


# Exact ASCII i + COMBINING DOT ABOVE (U+0307). Not a general combining-mark wipe.
_COMBINING_DOT_ABOVE = "\u0307"


def normalize_bulk_recipient_email(value: str | None) -> str:
    """Normalize a single bulk-email recipient address.

    Order: trim → Turkish letter map (ÜŞĞÇÖIİ + lower forms of ÜŞĞÇÖ) → lowercase
    → exact ``i`` + U+0307 → ``i``.
    İ maps to ASCII i (not Python default i+combining-dot). ı is not remapped.
    Safe to call repeatedly; does not change names or other fields.
    """
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    normalized = text.translate(_BULK_RECIPIENT_EMAIL_TR_MAP).lower()
    # Collapse i + combining-dot (e.g. legacy/corrupt local-part from İ mishandling).
    return normalized.replace(f"i{_COMBINING_DOT_ABOVE}", "i")


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
