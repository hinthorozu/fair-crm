"""HTTP fetch helpers for İstanbul Kitap Fuarı / legacy TÜYAP list pages."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

PAGINATION_HREF_PATTERN = re.compile(
    r"""<a[^>]+href=["']([^"']*page=\d+[^"']*)["']""",
    re.IGNORECASE,
)


def fetch_html(url: str, *, timeout: float = 30.0) -> str:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def normalize_page_url(href: str, *, base_url: str) -> str | None:
    cleaned = str(href).strip()
    if not cleaned or cleaned.startswith("#") or cleaned.lower().startswith("javascript:"):
        return None
    joined = urljoin(base_url, cleaned)
    parsed = urlparse(joined)
    if "page=" not in (parsed.query or "").lower():
        return None
    return urlunparse(parsed)


def discover_pagination_urls(html: str, *, base_url: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for href in PAGINATION_HREF_PATTERN.findall(html):
        page_url = normalize_page_url(href, base_url=base_url)
        if page_url is None or page_url in seen:
            continue
        seen.add(page_url)
        normalized.append(page_url)
    return normalized
