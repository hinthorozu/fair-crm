"""Same-domain website crawl for customer contact enrichment."""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

from app.modules.scraper.extractors.contact_extractor import normalize_website_url
from app.modules.scraper.fetchers.website_http_fetcher import fetch_html

CONTACT_PATH_KEYWORDS = (
    "iletisim",
    "contact",
    "hakkimizda",
    "hakkımızda",
    "about",
    "kurumsal",
    "corporate",
    "bize-ulasin",
    "reach-us",
)

HREF_PATTERN = re.compile(r"""href=["']([^"']+)["']""", re.IGNORECASE)


def _normalize_root_domain(netloc: str) -> str:
    host = netloc.lower().split(":", 1)[0]
    if host.startswith("www."):
        return host[4:]
    return host


def _same_domain(url: str, root_domain: str) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc:
        return True
    return _normalize_root_domain(parsed.netloc) == root_domain


def _is_contact_candidate(path: str) -> bool:
    lowered = path.lower()
    return any(keyword in lowered for keyword in CONTACT_PATH_KEYWORDS)


def discover_contact_links(html: str, *, base_url: str, root_domain: str) -> list[str]:
    discovered: list[str] = []
    seen: set[str] = set()
    for href in HREF_PATTERN.findall(html):
        normalized = normalize_website_url(urljoin(base_url, href))
        if normalized is None or normalized in seen:
            continue
        parsed = urlparse(normalized)
        if not _same_domain(normalized, root_domain) and not _is_social_url(normalized):
            continue
        if _is_social_url(normalized) or _is_contact_candidate(parsed.path):
            seen.add(normalized)
            discovered.append(normalized)
    return discovered


def _is_social_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(
        token in host
        for token in ("instagram.com", "facebook.com", "linkedin.com", "youtube.com", "youtu.be")
    )


def crawl_customer_website(
    website: str,
    *,
    max_pages: int = 10,
    fetcher: Callable[[str], str] | None = None,
) -> list[tuple[str, str]]:
    """Fetch the homepage and likely contact pages within the same domain."""
    start_url = normalize_website_url(website)
    if start_url is None:
        return []

    fetch = fetcher or fetch_html
    root_domain = _normalize_root_domain(urlparse(start_url).netloc)
    queue: list[str] = [start_url]
    visited: set[str] = set()
    pages: list[tuple[str, str]] = []

    while queue and len(pages) < max_pages:
        current_url = queue.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            html = fetch(current_url)
        except Exception:
            continue

        pages.append((current_url, html))

        for link in discover_contact_links(html, base_url=current_url, root_domain=root_domain):
            if _is_social_url(link):
                continue
            if link in visited or link in queue:
                continue
            if _same_domain(link, root_domain):
                queue.append(link)

    return pages
