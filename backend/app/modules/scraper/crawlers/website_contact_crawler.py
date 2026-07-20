"""Same-domain website crawl for customer contact enrichment."""

from __future__ import annotations

import re
from collections.abc import Callable
from html import unescape
from urllib.parse import urljoin, urlparse

from app.modules.scraper.extractors.contact_extractor import normalize_website_url
from app.modules.scraper.fetchers.website_http_fetcher import fetch_html

# Some sites serve a near-empty "loader" page at the bare domain/homepage and
# push the real content via a client-side redirect (meta refresh or
# `window.location`). A plain HTTP fetch never executes that JS, so the crawl
# would otherwise stop dead on an empty shell page. `STUB_REDIRECT_TEXT_LIMIT`
# bounds how little visible text a page may have before we treat a
# `window.location` assignment in it as a real redirect target rather than
# incidental JS on an otherwise content-rich page. Meta-refresh is always
# honored since it is an explicit page-level redirect directive.
STUB_REDIRECT_TEXT_LIMIT = 200
CLIENT_REDIRECT_MAX_HOPS = 3

META_REFRESH_PATTERN = re.compile(
    r"""<meta[^>]+http-equiv=["']refresh["'][^>]*content=["'][^"']*url=([^"'>]+)["']""",
    re.IGNORECASE,
)
JS_LOCATION_PATTERN = re.compile(
    r"""window\.location(?:\.href)?\s*=\s*["']([^"']+)["']"""
    r"""|window\.location\.replace\(\s*["']([^"']+)["']\s*\)""",
    re.IGNORECASE,
)
SCRIPT_OR_STYLE_PATTERN = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")

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


def _visible_text_length(html: str) -> int:
    """Approximate amount of visible page text, ignoring script/style and tags."""
    without_scripts = SCRIPT_OR_STYLE_PATTERN.sub(" ", html)
    text = TAG_PATTERN.sub(" ", without_scripts)
    return len(re.sub(r"\s+", "", text))


def detect_client_side_redirect(html: str, base_url: str) -> str | None:
    """Return the absolute target URL of a client-side redirect, if present.

    Handles the two common "loader" patterns that a plain HTTP fetch cannot
    follow on its own: `<meta http-equiv="refresh" content="...;url=...">`
    and a bare `window.location(.href) = "..."` / `window.location.replace(...)`
    script. The meta-refresh case is always honored. The `window.location`
    case is only honored when the page has little to no other visible
    content, so we don't hijack content-rich pages that merely also contain
    unrelated redirect JS elsewhere (e.g. login/logout handlers).
    """
    meta_match = META_REFRESH_PATTERN.search(html)
    if meta_match:
        target = unescape(meta_match.group(1).strip())
        if target:
            return urljoin(base_url, target)

    if _visible_text_length(html) <= STUB_REDIRECT_TEXT_LIMIT:
        js_match = JS_LOCATION_PATTERN.search(html)
        if js_match:
            target = unescape((js_match.group(1) or js_match.group(2) or "").strip())
            if target:
                return urljoin(base_url, target)

    return None


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

        for _ in range(CLIENT_REDIRECT_MAX_HOPS):
            redirect_target = detect_client_side_redirect(html, current_url)
            if redirect_target is None or redirect_target in visited:
                break
            if not _same_domain(redirect_target, root_domain):
                break
            visited.add(redirect_target)
            try:
                html = fetch(redirect_target)
            except Exception:
                break
            current_url = redirect_target

        pages.append((current_url, html))

        for link in discover_contact_links(html, base_url=current_url, root_domain=root_domain):
            if _is_social_url(link):
                continue
            if link in visited or link in queue:
                continue
            if _same_domain(link, root_domain):
                queue.append(link)

    return pages
