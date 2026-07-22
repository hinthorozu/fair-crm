import re
import unicodedata
from datetime import date
from urllib.parse import urlparse

from app.modules.fairs.domain.exceptions import InvalidFairSourceUrlError, InvalidFairWebsiteError
from app.modules.fairs.domain.value_objects import FairStatus

TURKISH_CHAR_MAP = str.maketrans(
    {
        "Ç": "C",
        "ç": "c",
        "Ğ": "G",
        "ğ": "g",
        "İ": "I",
        "I": "I",
        "ı": "i",
        "Ö": "O",
        "ö": "o",
        "Ş": "S",
        "ş": "s",
        "Ü": "U",
        "ü": "u",
    }
)


def normalize_fair_name(value: str) -> str:
    text = value.strip()
    if not text:
        return ""

    text = text.translate(TURKISH_CHAR_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_valid_fair_website(value: str) -> bool:
    """Accept protocol-less domains and http(s) URLs (abc.com, www.x.com, http(s)://...)."""
    text = value.strip()
    if not text:
        return True
    candidate = text if re.match(r"^https?://", text, flags=re.IGNORECASE) else f"https://{text}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False
    return host == "localhost" or "." in host


def normalize_website(value: str) -> str:
    """Store a consistent host (no scheme/www/path) so reopen display matches all input forms."""
    text = value.strip().lower()
    if not text:
        return ""
    if not is_valid_fair_website(text):
        raise InvalidFairWebsiteError(
            "website must be a domain or http(s) URL (e.g. abc.com or https://abc.com)"
        )
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^www\.", "", text)
    text = text.split("/")[0].split("?")[0]
    return text


def resolve_status_for_dates(
    *,
    requested_status: FairStatus | None,
    start_date: date | None,
    end_date: date | None,
    today: date,
    default: FairStatus = FairStatus.PLANNED,
) -> FairStatus:
    """Today/future start or end forces Planlandı; otherwise keep requested/default."""
    entered = [value for value in (start_date, end_date) if value is not None]
    if any(value >= today for value in entered):
        return FairStatus.PLANNED
    if requested_status is not None and requested_status != FairStatus.ARCHIVED:
        return requested_status
    return default


def compute_normalized_name(*, name: str) -> str:
    return normalize_fair_name(name)


def normalize_adapter_key(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    return text or None


def normalize_source_url(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidFairSourceUrlError("source_url must be a valid http or https URL")
    return text
