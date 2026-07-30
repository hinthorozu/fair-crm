"""Semicolon-separated multi-email normalization and validation."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import unquote

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

# Scrape/HTML candidates: keep only RFC-ish local/domain characters (no %).
_EMAIL_ALLOWED_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@._+-"
)
_MAILTO_PREFIX_RE = re.compile(r"^mailto:\s*", re.IGNORECASE)
# Bot-protection spellings: info[at]firma.com / info (at) firma [dot] com
_OBFUSCATED_AT_RE = re.compile(
    r"\s*[\[\(\{]\s*at\s*[\]\)\}]\s*",
    re.IGNORECASE,
)
_OBFUSCATED_DOT_RE = re.compile(
    r"\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*",
    re.IGNORECASE,
)
_MULTI_SPACE_RE = re.compile(r"\s+")


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


def cut_email_at_invalid_chars(value: str) -> str:
    """Keep only the leading run of allowed email characters; cut at the first other char."""
    chars: list[str] = []
    for ch in value:
        if ch not in _EMAIL_ALLOWED_CHARS:
            break
        chars.append(ch)
    return "".join(chars)


def deobfuscate_email_text(value: str) -> str:
    """Expand common bot-protection spellings before structural email cleanup.

    Examples: ``info[at]firma.com``, ``info (at) firma [dot] com``.
    ``at`` / ``dot`` matches are case-insensitive. Whitespace around those tokens
    is consumed by the replacements; unrelated internal whitespace is left so
    later validation can still reject malformed candidates.
    """
    text = _MULTI_SPACE_RE.sub(" ", value.strip())
    if not text:
        return ""
    text = _OBFUSCATED_AT_RE.sub("@", text)
    text = _OBFUSCATED_DOT_RE.sub(".", text)
    return _MULTI_SPACE_RE.sub(" ", text).strip()


def sanitize_scraped_email(raw: str | None) -> str | None:
    """Clean an email candidate and return a validated lowercase address.

    Shared by scraper extraction and Excel import. Handles mailto query/fragments,
    obfuscated at/dot spellings, HTML attribute/tag junk, and invalid characters.
    Returns None when the candidate cannot be normalized into a usable email.
    """
    if raw is None:
        return None
    text = unescape(str(raw)).strip()
    if not text:
        return None

    text = _MAILTO_PREFIX_RE.sub("", text).strip()
    text = unquote(text).strip()
    text = text.split("?", 1)[0].split("#", 1)[0]

    # Deobfuscate before cutting on brackets/parens used by [at] / (dot) forms.
    text = deobfuscate_email_text(text)

    for sep in ('"', "'", "<", ">", ",", ";", "\\"):
        if sep in text:
            text = text.split(sep, 1)[0]

    text = cut_email_at_invalid_chars(text).strip()
    if not text or "@" not in text:
        return None

    text = text.lower()
    if not is_valid_email_address(text):
        return None
    return text


def normalize_email_candidates(value: str | None) -> str | None:
    """Normalize one or more email candidates via ``sanitize_scraped_email``.

    Accepts comma- or semicolon-separated values. Unsalvageable parts are dropped
    (does not raise). Returns canonical ``a@x.com;b@y.com`` or None when nothing
    usable remains. Prefer this for import/scrape pipelines that should share one
    cleaning path; use ``normalize_email_field`` when invalid input must raise.
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None

    text = text.replace(",", ";")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in text.split(";"):
        part = raw.strip()
        if not part:
            continue
        cleaned = sanitize_scraped_email(part)
        if cleaned is None or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return ";".join(normalized) if normalized else None


def normalize_email_field(value: str | None) -> str | None:
    """Normalize a single or multi-email string to canonical `a@x.com;b@y.com` form."""
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    text = text.replace(",", ";")
    raw_parts = [part.strip() for part in text.split(";") if part.strip()]
    if not raw_parts:
        return None

    # Same sanitize path as scraper/import; raise when any part is unsalvageable.
    cleaned_parts: list[str] = []
    seen: set[str] = set()
    for raw in raw_parts:
        cleaned = sanitize_scraped_email(raw)
        if cleaned is None:
            if not is_valid_email_address(raw):
                raise ValueError(f"Invalid email address: {raw}")
            cleaned = raw.lower()
        if cleaned in seen:
            continue
        seen.add(cleaned)
        cleaned_parts.append(cleaned)

    return ";".join(cleaned_parts) if cleaned_parts else None
