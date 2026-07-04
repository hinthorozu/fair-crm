"""Shared website URL filtering for scraper parsers."""

from __future__ import annotations

from urllib.parse import urlparse

IGNORED_WEBSITE_HOST_FRAGMENTS: tuple[str, ...] = (
    "foodistexpo.com",
    "tuyap.com",
    "mytuyap.com",
    "cdn.mytuyap.com",
    "googleapis.com",
    "gstatic.com",
    "google.com",
    "googletagmanager.com",
    "google-analytics.com",
    "doubleclick.net",
    "useinsider.com",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "pinterest.com",
    "whatsapp.com",
    "w3.org",
    "schema.org",
)

IGNORED_WEBSITE_PATH_FRAGMENTS: tuple[str, ...] = (
    "/css",
    "/font",
    "/fonts",
    "/assets/css",
    "/gtm.js",
    "/ns.html",
)

IGNORED_WEBSITE_EXTENSIONS: tuple[str, ...] = (
    ".css",
    ".js",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".ico",
)


def normalize_website_url(url: str) -> str | None:
    cleaned = url.strip().rstrip(".,;)")
    if not cleaned:
        return None
    if cleaned.lower().startswith("www."):
        cleaned = f"https://{cleaned}"
    if not cleaned.lower().startswith(("http://", "https://")):
        return None
    return cleaned


def is_company_website(url: str) -> bool:
    lowered = url.lower().strip()
    if lowered.startswith(("mailto:", "tel:", "javascript:", "#")):
        return False

    normalized = normalize_website_url(url)
    if normalized is None:
        return False

    parsed = urlparse(normalized)
    host = parsed.netloc.lower().strip(".")
    if not host or host in {"-", "www.-", "localhost", "127.0.0.1"}:
        return False
    if host.replace(".", "").replace("-", "") == "":
        return False

    if any(fragment in host for fragment in IGNORED_WEBSITE_HOST_FRAGMENTS):
        return False

    path = (parsed.path or "").lower()
    if any(fragment in path for fragment in IGNORED_WEBSITE_PATH_FRAGMENTS):
        return False
    if any(path.endswith(ext) for ext in IGNORED_WEBSITE_EXTENSIONS):
        return False

    if "fonts.googleapis" in lowered or "fonts.gstatic" in lowered:
        return False

    return True


def pick_first_company_website(urls: list[str]) -> str | None:
    seen: set[str] = set()
    for raw in urls:
        normalized = normalize_website_url(raw)
        if normalized is None or not is_company_website(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        return normalized
    return None


SOCIAL_URL_FIELD_BY_HOST: tuple[tuple[str, str], ...] = (
    ("instagram.com", "instagram_url"),
    ("linkedin.com", "linkedin_url"),
    ("facebook.com", "facebook_url"),
    ("fb.com", "facebook_url"),
    ("youtube.com", "youtube_url"),
    ("youtu.be", "youtube_url"),
    ("twitter.com", "x_url"),
    ("x.com", "x_url"),
)

SOCIAL_URL_FIELDS: tuple[str, ...] = (
    "instagram_url",
    "linkedin_url",
    "facebook_url",
    "youtube_url",
    "x_url",
)


def classify_social_url(url: str) -> str | None:
    normalized = normalize_website_url(url)
    if normalized is None:
        return None

    host = urlparse(normalized).netloc.lower()
    for fragment, field_name in SOCIAL_URL_FIELD_BY_HOST:
        if fragment in host:
            return field_name
    return None


def extract_social_urls(urls: list[str]) -> dict[str, str]:
    social_urls: dict[str, str] = {}
    for raw in urls:
        normalized = normalize_website_url(raw)
        if normalized is None:
            continue
        field_name = classify_social_url(normalized)
        if field_name is None or field_name in social_urls:
            continue
        social_urls[field_name] = normalized
    return social_urls
