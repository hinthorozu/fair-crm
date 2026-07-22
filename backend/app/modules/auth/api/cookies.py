"""HttpOnly refresh-token cookie helpers."""

from __future__ import annotations

from typing import Literal

from fastapi import Request, Response

from app.core.config import Settings, get_settings

REFRESH_COOKIE_NAME = "fair_crm_refresh_token"
CSRF_HEADER_NAME = "X-Fair-CRM-Requested-With"
CSRF_HEADER_VALUE = "XMLHttpRequest"

SameSite = Literal["lax", "strict", "none"]


def refresh_cookie_max_age(settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    return int(cfg.refresh_token_expire_days) * 24 * 60 * 60


def _samesite(settings: Settings) -> SameSite:
    value = settings.refresh_cookie_samesite.lower()
    if value == "strict":
        return "strict"
    if value == "none":
        return "none"
    return "lax"


def set_refresh_cookie(response: Response, refresh_token: str, *, settings: Settings | None = None) -> None:
    cfg = settings or get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=refresh_cookie_max_age(cfg),
        httponly=True,
        secure=cfg.refresh_cookie_secure,
        samesite=_samesite(cfg),
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response, *, settings: Settings | None = None) -> None:
    cfg = settings or get_settings()
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        httponly=True,
        secure=cfg.refresh_cookie_secure,
        samesite=_samesite(cfg),
    )


def read_refresh_cookie(request: Request) -> str | None:
    value = request.cookies.get(REFRESH_COOKIE_NAME)
    if not value or not value.strip():
        return None
    return value.strip()


def csrf_header_ok(request: Request) -> bool:
    """Require custom header on cookie-auth mutating requests (CSRF mitigation)."""
    return request.headers.get(CSRF_HEADER_NAME) == CSRF_HEADER_VALUE
