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


def canonicalize_fair_name(value: str) -> str:
    """Stored fair name: Turkish-aware uppercase, independent of process locale.

    i becomes İ and ı becomes I before Unicode uppercase, so dotted and
    dotless letters stay distinct.
    """
    text = value.strip()
    if not text:
        return ""
    return text.translate({ord("i"): "İ", ord("ı"): "I"}).upper()


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


def system_fair_status_for_dates(
    *,
    start_date: date | None,
    end_date: date | None,
    today: date,
) -> FairStatus | None:
    """Lifecycle of a system fair from its calendar dates.

    Past when the end date is before today, current when today falls inside
    the inclusive start/end range, and planned when the start date is still
    ahead. Returns None when the dates do not decide.
    """
    if end_date is not None and end_date < today:
        return FairStatus.COMPLETED
    if start_date is not None and start_date > today:
        return FairStatus.PLANNED
    if start_date is not None and start_date <= today and (end_date is None or end_date >= today):
        return FairStatus.ACTIVE
    return None


def compute_normalized_name(*, name: str) -> str:
    return normalize_fair_name(name)


_YEAR_TOKEN = re.compile(r"^(?:19|20)\d{2}$")
_ORDINAL_TOKEN = re.compile(r"^(\d+)(?:ST|ND|RD|TH)$")


def _edition_number(token: str) -> str | None:
    """Edition marker carried in a fair name. Calendar years are not editions."""
    if _YEAR_TOKEN.fullmatch(token):
        return None
    if token.isdigit():
        return token
    ordinal = _ORDINAL_TOKEN.fullmatch(token)
    if ordinal is not None:
        return ordinal.group(1)
    return None


def compute_identity_name(*, name: str) -> str:
    """Persistent System Fair label.

    ``normalized_name`` keeps the official wording, including the calendar year
    and edition number. This label removes only those occurrence tokens so two
    years of the same fair can be compared. It does not merge same-year editions;
    callers still use :func:`edition_key` for that guard.
    """
    normalized = normalize_fair_name(name)
    kept = [
        token
        for token in normalized.split()
        if not _YEAR_TOKEN.fullmatch(token) and _edition_number(token) is None
    ]
    return " ".join(kept)


def edition_key(name: str) -> tuple[str, ...]:
    """Non-year numbers in a fair name, in order. Empty when the name has none."""
    normalized = normalize_fair_name(name)
    return tuple(
        number
        for token in normalized.split()
        if (number := _edition_number(token)) is not None
    )


def fair_city_key(city: str | None) -> str:
    return normalize_fair_name(city or "")


_DISPLAY_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_CATALOG_TAIL = re.compile(r"^(?:\d+\s*\.|ULUSLARARASI\b|\()")
_SEPARATORS = " \t-–—,.;/"


def _token_in_text(text: str, token: str) -> bool:
    if not token:
        return False
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", text) is not None


def system_fair_display_name(*, name: str, city: str | None, origin: str) -> str:
    """Short label for a system fair. Official ``name`` stays unchanged.

    Shortens only when a calendar year is followed by a TOBB catalog tail
    (edition number, ``ULUSLARARASI``, or a parenthetical section). Otherwise
    the official name is shown as-is.
    """
    if origin != "system":
        return name
    match = _DISPLAY_YEAR.search(name)
    if match is None:
        return name
    head = name[: match.start()].strip(_SEPARATORS)
    tail = name[match.end() :].strip(_SEPARATORS)
    if not head or head.startswith("(") or not tail:
        return name
    city_token = (city or "").strip()
    description = tail
    if city_token and tail.startswith(city_token):
        description = tail[len(city_token) :].strip(_SEPARATORS)
    if not description or _CATALOG_TAIL.match(description) is None:
        return name
    year = match.group(1)
    if city_token and not _token_in_text(head, city_token):
        return f"{head} {year} – {city_token}"
    return f"{head} {year}"


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
