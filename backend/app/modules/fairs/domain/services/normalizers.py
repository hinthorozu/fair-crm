import re
import unicodedata
from urllib.parse import urlparse

from app.modules.fairs.domain.exceptions import InvalidFairSourceUrlError

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


def normalize_website(value: str) -> str:
    text = value.strip().lower()
    if not text:
        return ""
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^www\.", "", text)
    text = text.split("/")[0].split("?")[0]
    return text


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
