"""UMCRM legacy data cleaning helpers (shared by clean script and tests)."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any
from urllib.parse import urlparse

from analyze_umcrm_duplicates import normalize_company_name

TURKISH_CHAR_MAP = str.maketrans(
    {
        "Ç": "c",
        "ç": "c",
        "Ğ": "g",
        "ğ": "g",
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ö": "o",
        "ö": "o",
        "Ş": "s",
        "ş": "s",
        "Ü": "u",
        "ü": "u",
    }
)

COMPANY_PLACEHOLDERS = {
    "test",
    "deneme",
    "null",
    "n/a",
    "na",
    "yok",
    "bilinmiyor",
    "unknown",
    "firma",
    "company",
    "-",
    ".",
}

EMAIL_PLACEHOLDERS = {
    "test@test.com",
    "info@test.com",
    "example@example.com",
    "noemail",
    "yok",
    "null",
    "n/a",
    "na",
    "-",
    "xxx@xxx.com",
    "xxx",
}

PHONE_PLACEHOLDERS = {
    "000",
    "0000",
    "00000",
    "000000",
    "0000000",
    "00000000",
    "123456",
    "111111",
    "1234567",
    "12345678",
    "yok",
    "null",
    "n/a",
    "-",
    "0",
}

WEBSITE_PLACEHOLDERS = {
    "yok",
    "null",
    "test",
    "www.test.com",
    "test.com",
    "example.com",
    "www.example.com",
    "n/a",
    "-",
    "xxx",
}

FAIR_PLACEHOLDERS = {
    "test",
    "deneme",
    "null",
    "yok",
    "unknown",
    "-",
}

SUSPICIOUS_FAIR_DATES = {"0000-00-00", "1970-01-01", "2126-01-01"}

EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

HTML_ENTITY_RE = re.compile(r"&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);")
MOJIBAKE_RE = re.compile(r"[ÃÄÅÆØÞÐÑÒÔÕÖ×ÙÚÛÜÝÞß]{2,}")
ENCODING_ARTIFACT_RE = re.compile(r"[\ufffd\u00c2\u00a0]")

MIN_COMPANY_NAME_LEN = 2
MAX_COMPANY_NAME_LEN = 200
MIN_PHONE_DIGITS = 7


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def decode_html_entities(text: str) -> str:
    if not text:
        return text
    if HTML_ENTITY_RE.search(text):
        return html.unescape(text)
    return text


def fix_mojibake(text: str) -> tuple[str, bool]:
    if not text or not (MOJIBAKE_RE.search(text) or ENCODING_ARTIFACT_RE.search(text)):
        return text, False
    candidates: list[str] = [text]
    for encoding in ("latin1", "cp1252", "latin5", "cp1254"):
        try:
            candidates.append(text.encode(encoding).decode("utf-8"))
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
    for candidate in candidates:
        if candidate != text and not MOJIBAKE_RE.search(candidate):
            return candidate, True
    return text.replace("\ufffd", "").replace("\u00a0", " "), False


def phone_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_valid_email(value: str) -> bool:
    if "@" not in value:
        return False
    if any(sep in value for sep in (" ", ",", ";")):
        return False
    local, domain = value.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        return False
    return bool(EMAIL_RE.match(value))


def looks_like_email(value: str) -> bool:
    return "@" in value and "." in value.split("@", 1)[1]


def looks_like_phone(value: str) -> bool:
    digits = phone_digits(value)
    return len(digits) >= 7 and len(digits) / max(len(value), 1) > 0.5


def normalize_website_host(value: str) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith("mailto:"):
        lowered = lowered.removeprefix("mailto:")
    if not lowered.startswith(("http://", "https://")):
        lowered = "http://" + lowered
    try:
        parsed = urlparse(lowered)
        host = (parsed.netloc or parsed.path).lower()
        host = host.removeprefix("www.")
        host = host.rstrip("/")
        return host or None
    except Exception:
        return lowered


def is_valid_website(value: str) -> bool:
    if looks_like_email(value) or looks_like_phone(value):
        return False
    if " " in value:
        return False
    host = normalize_website_host(value)
    if not host:
        return False
    if "." not in host and host not in WEBSITE_PLACEHOLDERS:
        return False
    return True


def normalize_website_url(value: str) -> tuple[str | None, bool]:
    text = clean_text(value)
    if not text:
        return None, False
    lowered = text.lower()
    if lowered in WEBSITE_PLACEHOLDERS:
        return None, False
    if looks_like_email(text) or looks_like_phone(text):
        return None, False
    if not is_valid_website(text):
        return None, False
    normalized = text
    was_normalized = False
    if not normalized.lower().startswith(("http://", "https://")):
        normalized = "https://" + normalized.lstrip("/")
        was_normalized = True
    return normalized, was_normalized


def normalize_phone_display(value: str) -> str:
    text = collapse_whitespace(value)
    text = re.sub(r"[/\\]{2,}", "/", text)
    text = re.sub(r"[-]+", "-", text)
    return text.strip(" -/")


def is_phone_placeholder(value: str) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered in PHONE_PLACEHOLDERS or stripped in PHONE_PLACEHOLDERS:
        return True
    digits = phone_digits(stripped)
    if digits and set(digits) == {"0"}:
        return True
    if digits and len(digits) < MIN_PHONE_DIGITS and not re.search(
        r"[a-zA-Z\u0080-\uFFFF]", stripped
    ):
        return True
    return False


def clean_fair_date(value: str | None) -> tuple[str | None, bool]:
    if not value:
        return None, False
    text = value.strip()
    if text in SUSPICIOUS_FAIR_DATES or text.startswith("0000") or text.startswith("2126"):
        return None, True
    if len(text) >= 10:
        return text[:10], False
    return text, False


def company_name_folded(name: str) -> str:
    folded = name.translate(TURKISH_CHAR_MAP).lower()
    folded = re.sub(r"[^\w\s]", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def clean_company_name(name: str) -> tuple[str, list[str], bool]:
    issues: list[str] = []
    manual_review = False
    original = name or ""
    text = original

    if HTML_ENTITY_RE.search(text):
        text = decode_html_entities(text)
        issues.append("html_entity_decoded")

    fixed, was_fixed = fix_mojibake(text)
    if was_fixed:
        text = fixed
        issues.append("encoding_fixed")
    elif MOJIBAKE_RE.search(text) or ENCODING_ARTIFACT_RE.search(text):
        issues.append("encoding_issue")
        manual_review = True

    text = collapse_whitespace(text)

    if not text:
        issues.append("empty_name")
        manual_review = True
    elif len(text) < MIN_COMPANY_NAME_LEN:
        issues.append("too_short")
        manual_review = True
    elif len(text) > MAX_COMPANY_NAME_LEN:
        issues.append("too_long")
        manual_review = True
    elif re.fullmatch(r"\d+", text):
        issues.append("digits_only")
        manual_review = True
    elif not re.search(r"[\w\u0080-\uFFFF]", text, re.UNICODE):
        issues.append("punctuation_only")
        manual_review = True
    elif company_name_folded(text) in COMPANY_PLACEHOLDERS:
        issues.append("placeholder_name")
        manual_review = True

    return text, issues, manual_review


def clean_company_phones(
    phone1: str | None,
    phone2: str | None,
    phone3: str | None,
) -> tuple[list[str], list[str], dict[str, int]]:
    stats = {"dropped_placeholder": 0, "dropped_empty": 0, "duplicate_merged": 0}
    issues: list[str] = []
    manual_review = False
    cleaned: list[str] = []
    seen_digits: set[str] = set()
    seen_text: set[str] = set()

    for raw in (phone1, phone2, phone3):
        if not raw or not raw.strip():
            stats["dropped_empty"] += 1
            continue
        stripped = raw.strip()
        if is_phone_placeholder(stripped):
            stats["dropped_placeholder"] += 1
            issues.append(f"dropped_placeholder_phone:{stripped}")
            continue

        display = normalize_phone_display(stripped)
        has_letters = bool(re.search(r"[a-zA-Z\u0080-\uFFFF]", stripped))
        if has_letters:
            issues.append("phone_contains_letters")
            manual_review = True
        elif re.search(r"[/\\|]", stripped) or len(stripped) > 25:
            issues.append("phone_contains_note")
            manual_review = True

        if has_letters:
            key = display.lower()
            if key in seen_text:
                stats["duplicate_merged"] += 1
                issues.append(f"duplicate_phone_merged:{display}")
                continue
            seen_text.add(key)
        else:
            digits = phone_digits(display)
            if not digits:
                stats["dropped_placeholder"] += 1
                issues.append(f"dropped_no_digits_phone:{stripped}")
                continue
            if digits in seen_digits:
                stats["duplicate_merged"] += 1
                issues.append(f"duplicate_phone_merged:{display}")
                continue
            seen_digits.add(digits)

        cleaned.append(display)

    if manual_review:
        issues.append("manual_review_phone")

    return cleaned, issues, stats


def clean_company_websites(
    web1: str | None,
    web2: str | None,
) -> tuple[list[str], list[str], dict[str, int]]:
    stats = {
        "dropped_empty": 0,
        "dropped_placeholder": 0,
        "dropped_invalid": 0,
        "normalized": 0,
        "duplicate_merged": 0,
    }
    issues: list[str] = []
    cleaned: list[str] = []
    seen_hosts: set[str] = set()

    for raw in (web1, web2):
        if not raw or not raw.strip():
            stats["dropped_empty"] += 1
            continue
        stripped = raw.strip()
        lowered = stripped.lower()
        if lowered in WEBSITE_PLACEHOLDERS:
            stats["dropped_placeholder"] += 1
            issues.append(f"dropped_placeholder_website:{stripped}")
            continue
        if looks_like_email(stripped):
            stats["dropped_invalid"] += 1
            issues.append(f"dropped_email_as_website:{stripped}")
            continue
        if looks_like_phone(stripped):
            stats["dropped_invalid"] += 1
            issues.append(f"dropped_phone_as_website:{stripped}")
            continue

        normalized, was_normalized = normalize_website_url(stripped)
        if not normalized:
            stats["dropped_invalid"] += 1
            issues.append(f"dropped_invalid_website:{stripped}")
            continue

        if was_normalized:
            stats["normalized"] += 1
            issues.append(f"website_scheme_added:{stripped}")

        host = normalize_website_host(normalized)
        if host and host in seen_hosts:
            stats["duplicate_merged"] += 1
            issues.append(f"duplicate_website_merged:{normalized}")
            continue
        if host:
            seen_hosts.add(host)
        cleaned.append(normalized)

    return cleaned, issues, stats


def sanitize_email_raw(value: str) -> str:
    text = value.strip().lower()
    text = text.replace(" ", "").replace(",", "").replace(";", "")
    return text


def clean_company_emails(
    email_rows: list[str],
    cross_company_duplicates: set[str] | None = None,
) -> tuple[list[str], list[str], list[str], dict[str, int]]:
    stats = {
        "dropped_empty": 0,
        "dropped_placeholder": 0,
        "dropped_invalid": 0,
        "duplicate_merged": 0,
    }
    issues: list[str] = []
    originals: list[str] = []
    cleaned: list[str] = []
    seen: set[str] = set()
    cross = cross_company_duplicates or set()

    for raw in email_rows:
        if not raw or not raw.strip():
            stats["dropped_empty"] += 1
            continue
        originals.append(raw)
        sanitized = sanitize_email_raw(raw)
        if not sanitized:
            stats["dropped_empty"] += 1
            issues.append("dropped_empty_email")
            continue
        if sanitized in EMAIL_PLACEHOLDERS:
            stats["dropped_placeholder"] += 1
            issues.append(f"dropped_placeholder_email:{raw}")
            continue
        if not is_valid_email(sanitized):
            stats["dropped_invalid"] += 1
            issues.append(f"dropped_invalid_email:{raw}")
            continue
        if sanitized in seen:
            stats["duplicate_merged"] += 1
            issues.append(f"duplicate_email_merged:{sanitized}")
            continue
        seen.add(sanitized)
        if sanitized in cross:
            issues.append(f"cross_company_duplicate_email:{sanitized}")
        cleaned.append(sanitized)

    return cleaned, originals, issues, stats


def clean_fair_record(
    fair_id: int,
    name: str,
    start_fair: str | None,
    end_fair: str | None,
    fair_area: str | None,
    fair_website: str | None,
    email_subject: str | None,
) -> dict[str, Any]:
    issues: list[str] = []
    manual_review = False
    name_original = name or ""

    name_clean = decode_html_entities(name_original)
    name_clean, name_issues, name_manual = clean_company_name(name_clean)
    issues.extend(name_issues)
    manual_review = manual_review or name_manual

    start_clean, start_nullified = clean_fair_date(start_fair)
    end_clean, end_nullified = clean_fair_date(end_fair)
    if start_nullified:
        issues.append("nullified_start_date")
    if end_nullified:
        issues.append("nullified_end_date")

    if start_clean and end_clean and end_clean < start_clean:
        issues.append("end_before_start")
        manual_review = True

    area_clean = collapse_whitespace(fair_area) if fair_area else None
    if area_clean and area_clean.lower() in {"yok", "null", "-", "n/a", "test"}:
        area_clean = None
        issues.append("nullified_fair_area")

    website_clean = None
    if fair_website and fair_website.strip():
        normalized, was_normalized = normalize_website_url(fair_website.strip())
        if normalized:
            website_clean = normalized
            if was_normalized:
                issues.append("website_scheme_added")
        else:
            issues.append(f"invalid_fair_website:{fair_website}")
            manual_review = True

    subject_clean = clean_text(email_subject)
    if subject_clean and subject_clean.lower() in {"null", "yok", "-", "test"}:
        subject_clean = None
        issues.append("nullified_email_subject")
    elif subject_clean:
        issues.append("email_subject_preserved_for_meta")

    return {
        "legacy_fair_id": fair_id,
        "name_original": name_original,
        "name_clean": name_clean,
        "start_date_clean": start_clean,
        "end_date_clean": end_clean,
        "fair_area_clean": area_clean,
        "website_clean": website_clean,
        "email_subject_clean": subject_clean,
        "manual_review": manual_review,
        "issues": issues,
    }


def clean_fair_relations(
    relations: list[tuple[int, int, int]],
    company_ids: set[int],
    fair_ids: set[int],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {
        "dropped_orphan": 0,
        "duplicate_dropped": 0,
        "kept": 0,
    }
    cleaned: list[dict[str, Any]] = []
    seen_pairs: set[tuple[int, int]] = set()

    for rel_id, fair_id, company_id in relations:
        issues: list[str] = []
        if company_id not in company_ids:
            stats["dropped_orphan"] += 1
            issues.append("orphan_missing_company")
            continue
        if fair_id not in fair_ids:
            stats["dropped_orphan"] += 1
            issues.append("orphan_missing_fair")
            continue

        pair = (fair_id, company_id)
        if pair in seen_pairs:
            stats["duplicate_dropped"] += 1
            issues.append("duplicate_relation_dropped")
            continue

        seen_pairs.add(pair)
        stats["kept"] += 1
        cleaned.append(
            {
                "legacy_fair_id": fair_id,
                "legacy_company_id": company_id,
                "legacy_relation_id": rel_id,
                "issues": issues,
            }
        )

    return cleaned, stats
