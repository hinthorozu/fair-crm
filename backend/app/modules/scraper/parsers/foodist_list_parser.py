"""Parse Foodist Expo / TÜYAP New brand list item text."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

DETAIL_MARKER_PATTERN = re.compile(r"Detayl[ıi]\s+[İI]ncele", re.IGNORECASE)
SALON_PATTERN = re.compile(r"Salon:\s*([A-Za-z0-9]+)")
STANT_PATTERN = re.compile(r"Stant:\s*([A-Za-z0-9\-\/]+)")
BRANDS_INLINE_PATTERN = re.compile(r"Marka(?:lar)?\s*:?\s*(.+)$", re.IGNORECASE)
LOGO_DUPLICATE_PATTERN = re.compile(r"^(\S{1,4})\s+\1\s+")
LOGO_PLACEHOLDER_PREFIX_PATTERN = re.compile(r"^(\S{1,4})\s+(?=\S)")
TEMSILCI_MARKER_PATTERN = re.compile(r"\s+Temsilcilikler\b", re.IGNORECASE)

KNOWN_COUNTRIES: tuple[str, ...] = (
    "Birleşik Arap Emirlikleri",
    "Türkiye",
    "Almanya",
    "Çin",
    "İtalya",
    "Fransa",
    "İspanya",
    "Hollanda",
    "İngiltere",
    "ABD",
    "Japonya",
    "Güney Kore",
    "Kore",
    "Hindistan",
    "Belçika",
    "İsviçre",
    "Avusturya",
    "Polonya",
    "Rusya",
    "Ukrayna",
    "Yunanistan",
    "Portekiz",
    "İsveç",
    "Norveç",
    "Danimarka",
    "Finlandiya",
    "Mısır",
    "Suudi Arabistan",
    "İran",
    "Pakistan",
    "Tayvan",
    "Vietnam",
    "Tayland",
    "Malezya",
    "Endonezya",
    "Brezilya",
    "Meksika",
    "Kanada",
    "Avustralya",
    "Suriye",
    "Irak",
    "Azerbaycan",
    "Amerika",
)

COUNTRY_ALIASES: dict[str, str] = {
    "turkiye": "Türkiye",
    "turkey": "Türkiye",
    "cin": "Çin",
    "cın": "Çin",
    "china": "Çin",
    "almanya": "Almanya",
    "germany": "Almanya",
    "italya": "İtalya",
    "italy": "İtalya",
    "fransa": "Fransa",
    "france": "Fransa",
    "ispanya": "İspanya",
    "spain": "İspanya",
    "hollanda": "Hollanda",
    "netherlands": "Hollanda",
    "ingiltere": "İngiltere",
    "united kingdom": "İngiltere",
    "uk": "İngiltere",
    "abd": "ABD",
    "usa": "ABD",
    "united states": "ABD",
    "amerika": "Amerika",
    "suriye": "Suriye",
    "syria": "Suriye",
    "irak": "Irak",
    "iraq": "Irak",
    "azerbaycan": "Azerbaycan",
    "azerbaijan": "Azerbaycan",
}


@dataclass(frozen=True)
class FoodistListItem:
    company_name: str
    country: str | None
    brands: str | None
    hall: str | None
    stand: str | None
    detail_url: str | None
    raw_text: str


def parse_foodist_list_text(text: str, *, detail_url: str | None = None) -> FoodistListItem | None:
    """Parse a Foodist brand list row into structured exhibitor fields."""
    normalized = _normalize_list_text(text)
    if not normalized:
        return None

    hall_match = SALON_PATTERN.search(normalized)
    stand_match = STANT_PATTERN.search(normalized)
    hall = hall_match.group(1) if hall_match else None
    stand = stand_match.group(1) if stand_match else None

    prefix = DETAIL_MARKER_PATTERN.split(normalized, maxsplit=1)[0].strip()
    prefix = _strip_logo_duplicate(prefix)
    if TEMSILCI_MARKER_PATTERN.search(prefix):
        prefix = TEMSILCI_MARKER_PATTERN.split(prefix, maxsplit=1)[0].strip()

    brands: str | None = None
    country: str | None = None
    brands_match = BRANDS_INLINE_PATTERN.search(prefix)
    if brands_match:
        brands_text = brands_match.group(1).strip()
        brands, country = _trim_trailing_country(brands_text)
        prefix = prefix[: brands_match.start()].strip()

    company_name, prefix_country = _split_company_and_country(prefix)
    if country is None:
        country = prefix_country
    if not company_name:
        return None

    return FoodistListItem(
        company_name=company_name,
        country=country,
        brands=brands,
        hall=hall,
        stand=stand,
        detail_url=detail_url,
        raw_text=normalized,
    )


def _trim_trailing_country(text: str) -> tuple[str, str | None]:
    cleaned = _normalize_list_text(text)
    if not cleaned:
        return "", None

    words = cleaned.split()
    for size in (3, 2, 1):
        if len(words) < size:
            continue
        tail = " ".join(words[-size:])
        country = _resolve_country_token(tail)
        if country is None:
            continue
        return " ".join(words[:-size]).strip(), country
    return cleaned, None


def _split_company_and_country(prefix: str) -> tuple[str, str | None]:
    cleaned = _normalize_list_text(prefix)
    if not cleaned:
        return "", None

    words = cleaned.split()
    for size in (3, 2, 1):
        if len(words) < size:
            continue
        tail = " ".join(words[-size:])
        country = _resolve_country_token(tail)
        if country is None:
            continue
        company_name = " ".join(words[:-size]).strip()
        if company_name:
            return company_name, country
        return "", country
    return cleaned, None


def _resolve_country_token(text: str) -> str | None:
    folded = _fold_text(text)
    for country in KNOWN_COUNTRIES:
        if _fold_text(country) == folded:
            return country
    return COUNTRY_ALIASES.get(folded)


def _normalize_list_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return " ".join(normalized.split()).strip()


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    without_marks = "".join(
        char for char in unicodedata.normalize("NFD", normalized) if unicodedata.category(char) != "Mn"
    )
    folded = " ".join(without_marks.split()).strip().casefold()
    return (
        folded.replace("ı", "i")
        .replace("ç", "c")
        .replace("ğ", "g")
        .replace("ö", "o")
        .replace("ş", "s")
        .replace("ü", "u")
        .replace("â", "a")
        .replace("î", "i")
        .replace("û", "u")
    )


def _strip_logo_duplicate(text: str) -> str:
    cleaned = LOGO_DUPLICATE_PATTERN.sub(r"\1 ", text).strip()
    return _strip_logo_placeholder_prefix(cleaned)


def _strip_logo_placeholder_prefix(text: str) -> str:
    """Drop a leading logo-placeholder token when it prefixes the company name.

    Foodist list rows sometimes flatten ``brand-logo-placeholder`` initials (e.g.
    ``AB``, ``AK``) ahead of the real ``h2.brand-name`` text. Only strip when the
    next token clearly continues those initials — never when it is unrelated
    (``AK STEEL`` keeps ``AK``).
    """
    match = LOGO_PLACEHOLDER_PREFIX_PATTERN.match(text)
    if not match:
        return text

    prefix = match.group(1)
    if not _looks_like_logo_placeholder(prefix):
        return text

    remainder = text[match.end() :].strip()
    if not remainder:
        return text

    next_token = remainder.split(maxsplit=1)[0]
    if _token_continues_logo_prefix(prefix, next_token):
        return remainder
    return text


def _looks_like_logo_placeholder(token: str) -> bool:
    compact = token.strip()
    if not compact or len(compact) > 4:
        return False
    return compact.isalnum()


def _token_continues_logo_prefix(prefix: str, next_token: str) -> bool:
    folded_prefix = _fold_text(prefix)
    folded_next = _fold_text(next_token)
    if folded_prefix == folded_next:
        return True
    if len(folded_next) <= len(folded_prefix):
        return False
    return folded_next.startswith(folded_prefix)
