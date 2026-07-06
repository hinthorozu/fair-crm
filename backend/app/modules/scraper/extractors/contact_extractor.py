"""Extract contact details from customer website HTML."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import unquote, urlparse

from app.modules.customers.domain.services.normalizers import normalize_email, normalize_phone
from app.modules.scraper.dto.enrichment_result_dto import SourcedValue

EMAIL_PATTERN = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
)
MAILTO_PATTERN = re.compile(
    r"""mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})""",
    re.IGNORECASE,
)
CFEMAIL_DATA_PATTERN = re.compile(
    r"""data-cfemail=["']([^"']+)["']""",
    re.IGNORECASE,
)
CFEMAIL_HREF_PATTERN = re.compile(
    r"""/cdn-cgi/l/email-protection#([0-9a-f]+)""",
    re.IGNORECASE,
)
TEL_PATTERN = re.compile(r"""tel:([+\d\s().\-/]+)""", re.IGNORECASE)
HREF_PATTERN = re.compile(r"""href=["']([^"']+)["']""", re.IGNORECASE)
PHONE_TEXT_PATTERN = re.compile(
    r"(?:\+?\d[\d\s().\-/]{7,}\d)",
)

JUNK_EMAIL_LOCALPARTS = frozenset(
    {
        "noreply",
        "no-reply",
        "no_reply",
        "donotreply",
        "do-not-reply",
        "example",
        "test",
        "sample",
        "mailer-daemon",
        "youremail",
        "yourname",
        "your",
        "username",
    }
)

JUNK_EMAIL_DOMAINS = frozenset(
    {
        "example.com",
        "test.com",
        "email.com",
    }
)

PLACEHOLDER_MAIL_COM_LOCALPARTS = frozenset(
    {
        "youremail",
        "yourname",
        "your",
        "suemail",
        "username",
        "example",
        "test",
        "sample",
        "name",
        "email",
        "mail",
    }
)

JUNK_EMAIL_TLD_SUFFIXES = frozenset(
    {"png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp", "tiff", "woff", "woff2"}
)

SOCIAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[^\s\"'<>]+", re.IGNORECASE),
    "facebook": re.compile(r"https?://(?:www\.)?(?:facebook\.com|fb\.com)/[^\s\"'<>]+", re.IGNORECASE),
    "linkedin": re.compile(r"https?://(?:[\w.]+\.)?linkedin\.com/[^\s\"'<>]+", re.IGNORECASE),
    "youtube": re.compile(r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s\"'<>]+", re.IGNORECASE),
}

ADDRESS_HINT_PATTERN = re.compile(
    r"(?:adres|address|konum|location)\s*[:\-]\s*(.{10,240})",
    re.IGNORECASE,
)


def is_junk_email(email: str) -> bool:
    lowered = email.strip().lower()
    if "@" not in lowered:
        return True
    local_part, domain = lowered.split("@", 1)
    if local_part in JUNK_EMAIL_LOCALPARTS:
        return True
    if "@2x" in local_part or local_part.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
        return True
    if domain in JUNK_EMAIL_DOMAINS or domain.endswith(".example.com") or domain.endswith(".test.com"):
        return True
    if local_part == "mail" and "example" in domain:
        return True
    if domain == "mail.com" and local_part in PLACEHOLDER_MAIL_COM_LOCALPARTS:
        return True
    tld = domain.rsplit(".", 1)[-1]
    return tld in JUNK_EMAIL_TLD_SUFFIXES


def normalize_website_url(url: str) -> str | None:
    cleaned = unescape(url.strip())
    if not cleaned or cleaned.startswith("#") or cleaned.lower().startswith("javascript:"):
        return None
    if not cleaned.lower().startswith(("http://", "https://")):
        cleaned = f"https://{cleaned.lstrip('/')}"
    parsed = urlparse(cleaned)
    if not parsed.netloc:
        return None
    return cleaned


def _clean_phone(value: str) -> str | None:
    normalized = normalize_phone(unquote(value))
    if len(normalized) < 10:
        return None
    if normalized.startswith("90") and len(normalized) == 12:
        return f"+{normalized}"
    if normalized.startswith("+"):
        return normalized
    return f"+{normalized}" if normalized.isdigit() else normalized


def _append_unique_sourced(
    items: list[SourcedValue],
    *,
    value: str,
    source_url: str,
    seen: set[str],
) -> None:
    key = value.strip().lower()
    if not key or key in seen:
        return
    seen.add(key)
    items.append(SourcedValue(value=value, source_url=source_url))


def decode_cfemail(encoded: str) -> str | None:
    """Decode Cloudflare email-protection hex (data-cfemail / cdn-cgi href)."""
    cleaned = encoded.strip().lower()
    if len(cleaned) < 4 or len(cleaned) % 2 != 0:
        return None
    if not re.fullmatch(r"[0-9a-f]+", cleaned):
        return None
    try:
        key = int(cleaned[:2], 16)
    except ValueError:
        return None
    chars: list[str] = []
    for index in range(2, len(cleaned), 2):
        try:
            chars.append(chr(int(cleaned[index : index + 2], 16) ^ key))
        except ValueError:
            return None
    email = "".join(chars).strip()
    return email or None


def _append_decoded_email(
    emails: list[SourcedValue],
    *,
    encoded: str,
    source_url: str,
    seen: set[str],
) -> None:
    decoded = decode_cfemail(encoded)
    if decoded is None:
        return
    email = normalize_email(decoded)
    if is_junk_email(email):
        return
    _append_unique_sourced(emails, value=email, source_url=source_url, seen=seen)


def extract_emails(html: str, source_url: str) -> list[SourcedValue]:
    seen: set[str] = set()
    emails: list[SourcedValue] = []

    for match in MAILTO_PATTERN.findall(html):
        email = normalize_email(unquote(match))
        if is_junk_email(email):
            continue
        _append_unique_sourced(emails, value=email, source_url=source_url, seen=seen)

    for match in CFEMAIL_DATA_PATTERN.findall(html):
        _append_decoded_email(emails, encoded=match, source_url=source_url, seen=seen)

    for match in CFEMAIL_HREF_PATTERN.findall(html):
        _append_decoded_email(emails, encoded=match, source_url=source_url, seen=seen)

    for match in EMAIL_PATTERN.findall(html):
        email = normalize_email(match)
        if is_junk_email(email):
            continue
        _append_unique_sourced(emails, value=email, source_url=source_url, seen=seen)

    return emails


def extract_phones(html: str, source_url: str) -> list[SourcedValue]:
    seen: set[str] = set()
    phones: list[SourcedValue] = []

    for match in TEL_PATTERN.findall(html):
        phone = _clean_phone(match)
        if phone is None:
            continue
        _append_unique_sourced(phones, value=phone, source_url=source_url, seen=seen)

    for match in PHONE_TEXT_PATTERN.findall(html):
        phone = _clean_phone(match)
        if phone is None:
            continue
        _append_unique_sourced(phones, value=phone, source_url=source_url, seen=seen)

    return phones


def extract_address(html: str, source_url: str) -> SourcedValue | None:
    text = re.sub(r"<[^>]+>", " ", unescape(html))
    text = re.sub(r"\s+", " ", text).strip()
    match = ADDRESS_HINT_PATTERN.search(text)
    if not match:
        return None
    value = match.group(1).strip(" .,-")
    if len(value) < 10:
        return None
    return SourcedValue(value=value, source_url=source_url)


def extract_social_links(html: str, source_url: str) -> dict[str, SourcedValue | None]:
    links: dict[str, SourcedValue | None] = {
        "instagram": None,
        "facebook": None,
        "linkedin": None,
        "youtube": None,
    }
    haystack = html
    for href in HREF_PATTERN.findall(html):
        haystack = f"{haystack} {href}"

    for key, pattern in SOCIAL_PATTERNS.items():
        match = pattern.search(haystack)
        if match is None:
            continue
        value = normalize_website_url(match.group(0))
        if value is None:
            continue
        links[key] = SourcedValue(value=value, source_url=source_url)
    return links


def extract_contacts_from_html(
    html: str,
    *,
    source_url: str,
    requested_fields: set[str],
) -> dict[str, object]:
    extracted: dict[str, object] = {}
    if "email" in requested_fields:
        extracted["emails"] = extract_emails(html, source_url)
    if "phone" in requested_fields:
        extracted["phones"] = extract_phones(html, source_url)
    if "address" in requested_fields:
        extracted["address"] = extract_address(html, source_url)
    social_fields = requested_fields & {"instagram", "facebook", "linkedin", "youtube"}
    if social_fields:
        social_links = extract_social_links(html, source_url)
        extracted["social_links"] = {
            key: social_links.get(key)
            for key in ("instagram", "facebook", "linkedin", "youtube")
            if key in social_fields
        }
    return extracted
