"""Parse İstanbul Kitap Fuarı exhibitor detail page HTML."""

from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup

from app.modules.scraper.parsers.website_filters import extract_social_urls

NO_ABOUT_TEXT = "bulunmamaktadır"


@dataclass(frozen=True)
class TuyapOldDetailInfo:
    about: str | None = None
    product_groups: tuple[str, ...] = ()
    email: str | None = None
    instagram_url: str | None = None
    linkedin_url: str | None = None
    facebook_url: str | None = None
    youtube_url: str | None = None


def parse_tuyap_old_detail_html(html: str) -> TuyapOldDetailInfo:
    soup = BeautifulSoup(html, "html.parser")

    about = _parse_about(soup)
    product_groups = _parse_product_groups(soup)
    email = _parse_email(soup)
    social_urls = _parse_social_links(soup)

    return TuyapOldDetailInfo(
        about=about,
        product_groups=product_groups,
        email=email,
        instagram_url=social_urls.get("instagram_url"),
        linkedin_url=social_urls.get("linkedin_url"),
        facebook_url=social_urls.get("facebook_url"),
        youtube_url=social_urls.get("youtube_url"),
    )


def _parse_about(soup: BeautifulSoup) -> str | None:
    tab = soup.select_one("#tab1") or soup.select_one(".tab-container__tab-content.active")
    if tab is None:
        return None

    paragraphs = [p.get_text(" ", strip=True) for p in tab.select("p")]
    text = "\n\n".join(part for part in paragraphs if part)
    if not text or NO_ABOUT_TEXT in text.lower():
        return None
    return text


def _parse_product_groups(soup: BeautifulSoup) -> tuple[str, ...]:
    wrapper = soup.select_one(".table-detail-wrapper__list")
    if wrapper is None:
        return ()

    groups: list[str] = []
    for item in wrapper.select("li.table-detail-wrapper__list-item"):
        text = item.get_text(" ", strip=True)
        if text:
            groups.append(text)
    return tuple(groups)


def _parse_email(soup: BeautifulSoup) -> str | None:
    contact_cell = soup.select_one('td[data-title="İletişim"]')
    if contact_cell is not None:
        email = _extract_mailto_from_tag(contact_cell)
        if email:
            return email

    for link in soup.select('a[href^="mailto:"]'):
        email = _extract_mailto_from_tag(link)
        if email:
            return email
    return None


def _parse_social_links(soup: BeautifulSoup) -> dict[str, str]:
    hrefs = [
        str(link.get("href", "")).strip()
        for link in soup.select(".detail-social-icons a[href]")
        if link.get("href")
    ]
    return extract_social_urls(hrefs)


def _extract_mailto_from_tag(tag) -> str | None:
    href = str(tag.get("href", "")).strip()
    if not href.lower().startswith("mailto:"):
        return None
    email = href[7:].split("?")[0].strip().lower()
    return email or None
