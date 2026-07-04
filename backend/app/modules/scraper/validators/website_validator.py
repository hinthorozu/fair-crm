"""Validate exhibitor website URLs with lightweight HTTP probes."""

from __future__ import annotations

import logging

import httpx

from app.modules.scraper.parsers.website_filters import is_company_website, normalize_website_url

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 8.0
_VALID_STATUS_CODES = frozenset(range(200, 400))
_CACHE: dict[str, bool] = {}


def validate_website_url(url: str | None, *, use_cache: bool = True) -> bool:
    if not url:
        return False

    normalized = normalize_website_url(url)
    if normalized is None or not is_company_website(normalized):
        return False

    if use_cache and normalized in _CACHE:
        return _CACHE[normalized]

    valid = _probe_url(normalized)
    if use_cache:
        _CACHE[normalized] = valid
    return valid


def clear_validation_cache() -> None:
    _CACHE.clear()


def _probe_url(url: str) -> bool:
    headers = {"User-Agent": "KYROX-Scraper/1.0 (+https://kyrox.local)"}
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT, follow_redirects=True, headers=headers) as client:
            response = client.head(url)
            if response.status_code in _VALID_STATUS_CODES:
                return True
            if response.status_code in {405, 403, 501}:
                return _probe_with_get(client, url)
            return False
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {405, 403, 501}:
            return _probe_with_get_standalone(url, headers=headers)
        return False
    except httpx.RequestError as exc:
        logger.debug("Website validation failed for %r: %s", url, exc)
        return _probe_with_get_standalone(url, headers=headers)


def _probe_with_get(client: httpx.Client, url: str) -> bool:
    try:
        response = client.get(url)
        return response.status_code in _VALID_STATUS_CODES
    except httpx.RequestError:
        return False


def _probe_with_get_standalone(url: str, *, headers: dict[str, str]) -> bool:
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            return response.status_code in _VALID_STATUS_CODES
    except httpx.RequestError:
        return False
