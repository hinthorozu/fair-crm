"""Canonical/import social URL field keys and resolution helpers."""

from __future__ import annotations

from typing import Any

from app.shared.url_normalization import normalize_optional_url

SOCIAL_URL_FIELD_PAIRS: tuple[tuple[str, str], ...] = (
    ("instagram_url", "instagram"),
    ("facebook_url", "facebook"),
    ("linkedin_url", "linkedin"),
    ("youtube_url", "youtube"),
)

CANONICAL_SOCIAL_FIELDS: frozenset[str] = frozenset(
    key for pair in SOCIAL_URL_FIELD_PAIRS for key in pair
)


def resolve_social_url(data: dict[str, Any], *, url_key: str, short_key: str) -> str | None:
    for key in (url_key, short_key):
        raw = data.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return normalize_optional_url(text)
    return None


def social_urls_from_mapping(data: dict[str, Any]) -> dict[str, str | None]:
    return {
        url_key: resolve_social_url(data, url_key=url_key, short_key=short_key)
        for url_key, short_key in SOCIAL_URL_FIELD_PAIRS
    }
