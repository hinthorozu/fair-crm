"""HTTP fetch helpers for Foodist Expo list/detail pages when Playwright is unavailable."""

from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx

from app.modules.scraper.parsers.foodist_list_extract import extract_list_text_from_brand_link_html

BRAND_LINK_PATTERN = re.compile(
    r'<a[^>]+href=["\']([^"\']*brand/[^"\']+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
PAGINATION_HREF_PATTERN = re.compile(
    r"""<a[^>]+href=["']([^"']*katilimci-listesi[^"']*)["']""",
    re.IGNORECASE,
)
LIST_PAGE_HREF_PATTERN = re.compile(
    r"""<a[^>]+href=["']([^"']+)["'][^>]*>""",
    re.IGNORECASE,
)


def fetch_html(url: str, *, timeout: float = 30.0) -> str:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def extract_list_items(html: str, *, base_url: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for href, inner_html in BRAND_LINK_PATTERN.findall(html):
        detail_url = urljoin(base_url, href.strip())
        list_text = extract_list_text_from_brand_link_html(inner_html)
        if not list_text or "brand/" not in detail_url:
            continue
        items.append({"detail_url": detail_url, "list_text": list_text})
    return items


def discover_pagination_urls(html: str, *, base_url: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for href in LIST_PAGE_HREF_PATTERN.findall(html):
        if "katilimci-listesi" not in href.lower():
            continue
        page_url = urljoin(base_url, href.strip())
        if page_url in seen:
            continue
        seen.add(page_url)
        normalized.append(page_url)
    return normalized


