"""Auth bridge (Core proxy + HttpOnly refresh cookie) tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.api.cookies import CSRF_HEADER_NAME, CSRF_HEADER_VALUE, REFRESH_COOKIE_NAME
from app.modules.auth.api.dependencies import get_core_auth_client
from app.modules.auth.infrastructure.core_auth_client import CoreAuthError, CoreTokenPair

FIFTEEN_DAYS_SECONDS = 15 * 24 * 60 * 60


@pytest.fixture
def mock_core_auth() -> MagicMock:
    return MagicMock()


@pytest.fixture
def auth_client(mock_core_auth: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_core_auth_client] = lambda: mock_core_auth
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _pair(
    *,
    access: str = "access-1",
    refresh: str = "refresh-1",
    expires_in: int = FIFTEEN_DAYS_SECONDS,
) -> CoreTokenPair:
    return CoreTokenPair(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=expires_in,
    )


def test_login_sets_httponly_refresh_cookie_and_returns_access_only(
    auth_client: TestClient, mock_core_auth: MagicMock
) -> None:
    mock_core_auth.login.return_value = _pair(
        access="jwt-access",
        refresh="opaque-refresh",
        expires_in=FIFTEEN_DAYS_SECONDS,
    )

    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "dev@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "jwt-access"
    assert body["expires_in"] == FIFTEEN_DAYS_SECONDS
    assert "refresh_token" not in body

    cookie = response.cookies.get(REFRESH_COOKIE_NAME)
    assert cookie == "opaque-refresh"
    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()
    assert "fair_crm_refresh_token=" in set_cookie
    assert f"Max-Age={FIFTEEN_DAYS_SECONDS}" in set_cookie or f"max-age={FIFTEEN_DAYS_SECONDS}" in set_cookie.lower()


def test_refresh_rotates_cookie_and_rejects_without_csrf(
    auth_client: TestClient, mock_core_auth: MagicMock
) -> None:
    mock_core_auth.refresh.return_value = _pair(
        access="jwt-2", refresh="refresh-2", expires_in=FIFTEEN_DAYS_SECONDS
    )
    auth_client.cookies.set(REFRESH_COOKIE_NAME, "refresh-1", path="/api/v1/auth")

    denied = auth_client.post("/api/v1/auth/refresh", json={})
    assert denied.status_code == 403
    mock_core_auth.refresh.assert_not_called()

    ok = auth_client.post(
        "/api/v1/auth/refresh",
        json={},
        headers={CSRF_HEADER_NAME: CSRF_HEADER_VALUE},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"] == "jwt-2"
    mock_core_auth.refresh.assert_called_once_with(refresh_token="refresh-1")
    assert ok.cookies.get(REFRESH_COOKIE_NAME) == "refresh-2"


def test_refresh_rejects_invalid_token_and_clears_cookie(
    auth_client: TestClient, mock_core_auth: MagicMock
) -> None:
    mock_core_auth.refresh.side_effect = CoreAuthError("Invalid refresh token", status_code=401)
    auth_client.cookies.set(REFRESH_COOKIE_NAME, "bad-token", path="/api/v1/auth")

    response = auth_client.post(
        "/api/v1/auth/refresh",
        json={},
        headers={CSRF_HEADER_NAME: CSRF_HEADER_VALUE},
    )
    assert response.status_code == 401
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert REFRESH_COOKIE_NAME in set_cookie
    assert "max-age=0" in set_cookie or "expires=" in set_cookie


def test_refresh_legacy_body_token_supported(
    auth_client: TestClient, mock_core_auth: MagicMock
) -> None:
    mock_core_auth.refresh.return_value = _pair(access="jwt-legacy", refresh="refresh-new")

    response = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "legacy-refresh"},
        headers={CSRF_HEADER_NAME: CSRF_HEADER_VALUE},
    )
    assert response.status_code == 200
    mock_core_auth.refresh.assert_called_once_with(refresh_token="legacy-refresh")
    assert response.cookies.get(REFRESH_COOKIE_NAME) == "refresh-new"


def test_logout_revokes_and_clears_cookie(
    auth_client: TestClient, mock_core_auth: MagicMock
) -> None:
    auth_client.cookies.set(REFRESH_COOKIE_NAME, "refresh-live", path="/api/v1/auth")

    response = auth_client.post(
        "/api/v1/auth/logout",
        json={},
        headers={CSRF_HEADER_NAME: CSRF_HEADER_VALUE},
    )
    assert response.status_code == 204
    mock_core_auth.logout.assert_called_once_with(refresh_token="refresh-live")
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert REFRESH_COOKIE_NAME in set_cookie


def test_session_config_exposes_15_day_ttls(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/auth/session-config")
    assert response.status_code == 200
    data = response.json()
    assert data["access_token_expire_days"] == 15
    assert data["refresh_token_expire_days"] == 15
    assert data["access_token_expire_seconds"] == FIFTEEN_DAYS_SECONDS
    assert data["refresh_cookie_max_age_seconds"] == FIFTEEN_DAYS_SECONDS
    assert "access_token_expire_minutes" not in data


def test_refresh_cookie_max_age_is_exactly_15_days() -> None:
    from app.core.config import Settings
    from app.modules.auth.api.cookies import refresh_cookie_max_age

    settings = Settings(
        access_token_expire_days=15,
        refresh_token_expire_days=15,
        app_env="test",
        refresh_cookie_secure=False,
        refresh_cookie_samesite="lax",
    )
    assert refresh_cookie_max_age(settings) == FIFTEEN_DAYS_SECONDS
