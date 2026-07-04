"""Parse Foodist Expo / TÜYAP New brand detail page HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape

from bs4 import BeautifulSoup, Tag

from app.modules.scraper.parsers.website_filters import (
    extract_social_urls,
    is_company_website,
    normalize_website_url,
    pick_first_company_website,
)

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{3}\)?[\s\-]?)?\d{3}[\s\-]?\d{2,3}[\s\-]?\d{2,4}"
)
ADDRESS_PATTERN = re.compile(
    r"(?:Adres|Address)\s*:?\s*(.+?)(?=(?:Telefon|Phone|E-posta|Email|Kategori|Category|Açıklama|Description)\s*:|$)",
    re.IGNORECASE,
)
CATEGORY_PATTERN = re.compile(
    r"(?:Kategori|Category)\s*:?\s*(.+?)(?=(?:Açıklama|Description|Adres|Address)\s*:|$)",
    re.IGNORECASE,
)
DESCRIPTION_PATTERN = re.compile(
    r"(?:Açıklama|Description)\s*:?\s*(.+?)(?:\.(?=\s*(?:Website|Site|Mail|Call)\b)|\.(?=\s*$)|$)",
    re.IGNORECASE,
)

DETAIL_CONTAINER_SELECTORS: tuple[str, ...] = (
    "table.company-info",
    "table.brand-info",
    "table.firm-info",
    ".company-detail table",
    ".schedule-single-wrap",
    ".schedule-detail",
    ".company-detail",
    ".schedule-detail-info",
    "[class*='company-info']",
    "[class*='contact-info']",
    ".schedule-sidebar .schedule-list",
    ".schedule-sidebar",
)

REMOVED_BODY_TAGS: tuple[str, ...] = ("script", "style", "link", "meta", "noscript")


@dataclass(frozen=True)
class FoodistDetailInfo:
    website: str | None = None
    websites: tuple[str, ...] = field(default_factory=tuple)
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    category: str | None = None
    description: str | None = None
    instagram_url: str | None = None
    linkedin_url: str | None = None
    facebook_url: str | None = None
    youtube_url: str | None = None
    x_url: str | None = None


def parse_foodist_detail_html(html: str) -> FoodistDetailInfo:
    """Extract contact and profile fields from a brand detail page."""
    soup = _prepare_body_soup(html)
    container = _find_company_detail_container(soup)
    container_html = str(container) if container is not None else ""
    container_text = _tag_to_text(container) if container is not None else ""

    text = container_text or _html_to_text(html)
    emails = _extract_emails(container_html or html, text)
    phones = _extract_phones(container_html or html, text)
    websites = _extract_websites_from_container(container)
    social_urls = _extract_social_urls_from_container(container)

    return FoodistDetailInfo(
        website=websites[0] if websites else None,
        websites=tuple(websites),
        phone=phones[0] if phones else None,
        email=emails[0] if emails else None,
        address=_extract_labeled_value(text, ADDRESS_PATTERN),
        category=_extract_labeled_value(text, CATEGORY_PATTERN),
        description=_extract_labeled_value(text, DESCRIPTION_PATTERN),
        instagram_url=social_urls.get("instagram_url"),
        linkedin_url=social_urls.get("linkedin_url"),
        facebook_url=social_urls.get("facebook_url"),
        youtube_url=social_urls.get("youtube_url"),
        x_url=social_urls.get("x_url"),
    )


def _prepare_body_soup(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    if soup.body is None:
        return soup

    for tag_name in REMOVED_BODY_TAGS:
        for tag in soup.body.find_all(tag_name):
            tag.decompose()
    return soup


def _find_company_detail_container(soup: BeautifulSoup) -> Tag | None:
    if soup.body is None:
        return None

    for selector in DETAIL_CONTAINER_SELECTORS:
        match = soup.body.select_one(selector)
        if match is not None and _tag_to_text(match):
            return match
    return None


def _extract_websites_from_container(container: Tag | None) -> list[str]:
    if container is None:
        return []

    candidates: list[str] = []
    for anchor in container.find_all("a", href=True):
        href = anchor.get("href")
        if not href:
            continue
        normalized = normalize_website_url(str(href).strip())
        if normalized is None:
            continue
        candidates.append(normalized)

    company_websites = [url for url in candidates if is_company_website(url)]
    primary = pick_first_company_website(company_websites)
    if primary is None:
        return []
    return [primary, *[url for url in company_websites if url != primary]]


def _extract_social_urls_from_container(container: Tag | None) -> dict[str, str]:
    if container is None:
        return {}

    hrefs: list[str] = []
    for anchor in container.find_all("a", href=True):
        href = anchor.get("href")
        if not href:
            continue
        normalized = normalize_website_url(str(href).strip())
        if normalized is not None:
            hrefs.append(normalized)

    return extract_social_urls(hrefs)


def _tag_to_text(tag: Tag) -> str:
    plain = tag.get_text(separator=" ", strip=True)
    return " ".join(unescape(plain).split())


def _html_to_text(html: str) -> str:
    without_scripts = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    without_styles = re.sub(r"<style[^>]*>.*?</style>", " ", without_scripts, flags=re.IGNORECASE | re.DOTALL)
    plain = re.sub(r"<[^>]+>", " ", without_styles)
    return " ".join(unescape(plain).split())


def _extract_emails(html: str, text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    for source in (html, text):
        for match in EMAIL_PATTERN.findall(source):
            email = match.strip().lower()
            if email in seen:
                continue
            seen.add(email)
            found.append(email)

    for match in re.finditer(r"""href=["']mailto:([^"']+)["']""", html, re.IGNORECASE):
        email = match.group(1).split("?")[0].strip().lower()
        if email and email not in seen:
            seen.add(email)
            found.append(email)

    return found


def _extract_phones(html: str, text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    for match in re.finditer(r"""href=["']tel:([^"']+)["']""", html, re.IGNORECASE):
        phone = _normalize_phone(match.group(1))
        if phone and phone not in seen:
            seen.add(phone)
            found.append(phone)

    for source in (text,):
        for match in PHONE_PATTERN.findall(source):
            phone = _normalize_phone(match)
            if not phone or len(re.sub(r"\D", "", phone)) < 10:
                continue
            if phone in seen:
                continue
            seen.add(phone)
            found.append(phone)

    return found


def _extract_labeled_value(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    value = match.group(1).strip()
    if pattern is DESCRIPTION_PATTERN and value and not value.endswith("."):
        value = f"{value}."
    return value or None


def _normalize_phone(value: str) -> str:
    return " ".join(value.replace("%20", " ").split())
