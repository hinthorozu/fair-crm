"""HTTP fetch helpers for customer website enrichment."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_USER_AGENT = "FairCRM-ContactEnrichment/1.0"


@dataclass(frozen=True)
class WebsiteFetchResult:
    html: str | None
    status_code: int | None
    error: str | None


def fetch_html_with_status(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    user_agent: str = DEFAULT_USER_AGENT,
) -> WebsiteFetchResult:
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            return WebsiteFetchResult(html=response.text, status_code=response.status_code, error=None)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        return WebsiteFetchResult(html=None, status_code=status_code, error=str(exc))
    except Exception as exc:
        return WebsiteFetchResult(html=None, status_code=None, error=str(exc))


def fetch_html(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    user_agent: str = DEFAULT_USER_AGENT,
) -> str:
    result = fetch_html_with_status(url, timeout=timeout, user_agent=user_agent)
    if result.html is None:
        raise RuntimeError(result.error or f"Failed to fetch {url}")
    return result.html
