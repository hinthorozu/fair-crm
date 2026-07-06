"""Parse İstanbul Kitap Fuarı / legacy TÜYAP exhibitor list HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

SALON_PATTERN = re.compile(r"Salon:\s*([A-Za-z0-9 /]+)", re.IGNORECASE)
STANT_PATTERN = re.compile(r"Stant:\s*([A-Za-z0-9\-/A-Za-z]+)", re.IGNORECASE)
NO_PRODUCT_GROUPS_TEXT = "ürün grubu bulunmamaktadır"


@dataclass(frozen=True)
class TuyapOldListItem:
    company_name: str
    detail_url: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    hall: str | None = None
    stand: str | None = None
    product_groups: tuple[str, ...] = ()


def parse_tuyap_old_list_html(html: str, *, base_url: str) -> list[TuyapOldListItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[TuyapOldListItem] = []
    for block in soup.select("div.filter-list__item"):
        parsed = _parse_list_item(block, base_url=base_url)
        if parsed is not None:
            items.append(parsed)
    return items


def _parse_list_item(block: Tag, *, base_url: str) -> TuyapOldListItem | None:
    table = block.select_one("table.filter-table")
    if table is None:
        return None

    firma_cell = table.select_one('td[data-title="Firma Adı"]')
    if firma_cell is None:
        return None

    content_blocks = firma_cell.select("div.table-block-content")
    if not content_blocks:
        return None

    company_name = _clean_text(content_blocks[0].get_text(" ", strip=True))
    if not company_name:
        return None

    address = _clean_text(content_blocks[1].get_text(" ", strip=True)) if len(content_blocks) > 1 else None

    phone = None
    email = None
    website = None
    contact_cell = table.select_one('td[data-title="İletişim"]')
    if contact_cell is not None:
        tel_link = contact_cell.select_one('a[href^="tel:"]')
        if tel_link is not None:
            phone = _clean_phone(tel_link.get("href", ""), tel_link.get_text(" ", strip=True))
        email = _extract_email(contact_cell)
        website = _extract_website(contact_cell)

    hall = None
    stand = None
    location_cell = table.select_one('td[data-title="Konum"]')
    if location_cell is not None:
        salon_el = location_cell.select_one(".salon span")
        if salon_el is not None:
            hall = _extract_labeled_value(salon_el.get_text(" ", strip=True), SALON_PATTERN)
        stand_el = location_cell.select_one(".stand")
        if stand_el is not None:
            stand = _extract_labeled_value(stand_el.get_text(" ", strip=True), STANT_PATTERN)

    detail_url = None
    detail_link = table.select_one("a.detail-button[href]")
    if detail_link is not None:
        detail_url = urljoin(base_url, str(detail_link.get("href", "")).strip())

    product_groups = _parse_product_groups(table)

    return TuyapOldListItem(
        company_name=company_name,
        detail_url=detail_url,
        address=address,
        email=email,
        phone=phone,
        website=website,
        hall=hall,
        stand=stand,
        product_groups=product_groups,
    )


def _parse_product_groups(table: Tag) -> tuple[str, ...]:
    wrapper = table.select_one(".table-detail-wrapper__list")
    if wrapper is None:
        return ()

    groups: list[str] = []
    for item in wrapper.select("li.table-detail-wrapper__list-item"):
        text = _clean_text(item.get_text(" ", strip=True))
        if text:
            groups.append(text)

    if groups:
        return tuple(groups)

    fallback = _clean_text(wrapper.get_text(" ", strip=True))
    if fallback and NO_PRODUCT_GROUPS_TEXT not in fallback.lower():
        return (fallback,)
    return ()


def _extract_email(contact_cell: Tag) -> str | None:
    mail_link = contact_cell.select_one('a[href^="mailto:"]')
    if mail_link is None:
        return None
    href = str(mail_link.get("href", "")).strip()
    if not href.lower().startswith("mailto:"):
        return None
    email = href[7:].split("?")[0].strip().lower()
    return email or None


def _extract_website(contact_cell: Tag) -> str | None:
    for link in contact_cell.select("a[href]"):
        href = str(link.get("href", "")).strip()
        if not href or href.startswith("tel:"):
            continue
        if "istanbulkitapfuari.com" in href.lower():
            continue
        return href
    return None


def _extract_labeled_value(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text or "")
    if not match:
        return None
    return _clean_text(match.group(1))


def _clean_phone(href: str, visible: str) -> str | None:
    raw = href.replace("tel:", "").strip() if href.startswith("tel:") else visible
    return _clean_text(raw)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None
