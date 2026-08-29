"""P0.2 onboarding/auth bridge route tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.api.cookies import REFRESH_COOKIE_NAME
from app.modules.auth.api.dependencies import get_core_auth_client
from app.modules.auth.infrastructure.core_auth_client import CoreAuthError, CoreAuthMessage


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


def test_signup_bridge_forwards_to_core_and_returns_202(
    auth_client: TestClient,
    mock_core_auth: MagicMock,
) -> None:
    mock_core_auth.signup.return_value = CoreAuthMessage(message="Signup accepted")

    response = auth_client.post(
        "/api/v1/auth/signup",
        json={
            "organization_name": "Acme Turkey",
            "email": "admin@example.com",
            "organization_slug": "acme-turkey",
        },
    )

    assert response.status_code == 202
    assert response.json() == {"message": "Signup accepted"}
    mock_core_auth.signup.assert_called_once_with(
        organization_name="Acme Turkey",
        email="admin@example.com",
        organization_slug="acme-turkey",
    )


def test_activation_bridge_forwards_token_and_password_without_local_policy(
    auth_client: TestClient,
    mock_core_auth: MagicMock,
) -> None:
    mock_core_auth.complete_activation.return_value = CoreAuthMessage(
        message="Account activated"
    )

    response = auth_client.post(
        "/api/v1/auth/activation/complete",
        json={"token": "activation-token", "password": "short-forwarded"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Account activated"}
    mock_core_auth.complete_activation.assert_called_once_with(
        token="activation-token",
        password="short-forwarded",
    )


def test_forgot_password_bridge_is_public_and_returns_core_message(
    auth_client: TestClient,
    mock_core_auth: MagicMock,
) -> None:
    mock_core_auth.forgot_password.return_value = CoreAuthMessage(
        message="If the account is eligible, check your email."
    )

    response = auth_client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "unknown@example.com"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "message": "If the account is eligible, check your email."
    }
    mock_core_auth.forgot_password.assert_called_once_with(
        email="unknown@example.com"
    )


def test_reset_password_bridge_clears_refresh_cookie_after_success(
    auth_client: TestClient,
    mock_core_auth: MagicMock,
) -> None:
    mock_core_auth.reset_password.return_value = CoreAuthMessage(
        message="Password reset. Sign in again."
    )
    auth_client.cookies.set(
        REFRESH_COOKIE_NAME,
        "stale-refresh",
        path="/api/v1/auth",
    )

    response = auth_client.post(
        "/api/v1/auth/password/reset",
        json={"token": "reset-token", "password": "new-password-forwarded"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password reset. Sign in again."}
    mock_core_auth.reset_password.assert_called_once_with(
        token="reset-token",
        password="new-password-forwarded",
    )
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert REFRESH_COOKIE_NAME in set_cookie
    assert "max-age=0" in set_cookie or "expires=" in set_cookie


@pytest.mark.parametrize(
    "authorization",
    [None, "", "Basic abc", "Bearer", "Bearer one two"],
)
def test_change_password_requires_one_bearer_access_token(
    auth_client: TestClient,
    mock_core_auth: MagicMock,
    authorization: str | None,
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}

    response = auth_client.post(
        "/api/v1/auth/password/change",
        json={
            "current_password": "current-password",
            "new_password": "new-password-forwarded",
        },
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Bearer access token required"}
    mock_core_auth.change_password.assert_not_called()


def test_change_password_forwards_bearer_without_csrf_and_clears_cookie(
    auth_client: TestClient,
    mock_core_auth: MagicMock,
) -> None:
    mock_core_auth.change_password.return_value = CoreAuthMessage(
        message="Password changed. Sign in again."
    )
    auth_client.cookies.set(
        REFRESH_COOKIE_NAME,
        "stale-refresh",
        path="/api/v1/auth",
    )

    response = auth_client.post(
        "/api/v1/auth/password/change",
        json={
            "current_password": "current-password",
            "new_password": "short-forwarded",
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password changed. Sign in again."}
    mock_core_auth.change_password.assert_called_once_with(
        access_token="access-token",
        current_password="current-password",
        new_password="short-forwarded",
    )
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert REFRESH_COOKIE_NAME in set_cookie
    assert "max-age=0" in set_cookie or "expires=" in set_cookie


@pytest.mark.parametrize(
    ("path", "payload", "method_name", "status_code", "detail"),
    [
        (
            "/api/v1/auth/signup",
            {"organization_name": "Acme", "email": "admin@example.com"},
            "signup",
            409,
            "Signup conflict",
        ),
        (
            "/api/v1/auth/activation/complete",
            {"token": "bad-token", "password": "password"},
            "complete_activation",
            400,
            "Invalid or expired activation token",
        ),
        (
            "/api/v1/auth/password/reset",
            {"token": "reset-token", "password": "weak"},
            "reset_password",
            422,
            "Password does not meet policy",
        ),
    ],
)
def test_onboarding_bridge_preserves_safe_core_error_contract(
    auth_client: TestClient,
    mock_core_auth: MagicMock,
    path: str,
    payload: dict,
    method_name: str,
    status_code: int,
    detail: str,
) -> None:
    getattr(mock_core_auth, method_name).side_effect = CoreAuthError(
        detail,
        status_code=status_code,
    )

    response = auth_client.post(path, json=payload)

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


def test_change_password_core_error_does_not_clear_cookie_before_success(
    auth_client: TestClient,
    mock_core_auth: MagicMock,
) -> None:
    mock_core_auth.change_password.side_effect = CoreAuthError(
        "Current password is incorrect",
        status_code=400,
    )
    auth_client.cookies.set(
        REFRESH_COOKIE_NAME,
        "still-live-refresh",
        path="/api/v1/auth",
    )

    response = auth_client.post(
        "/api/v1/auth/password/change",
        json={
            "current_password": "wrong",
            "new_password": "new-password-forwarded",
        },
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Current password is incorrect"}
    assert REFRESH_COOKIE_NAME not in response.headers.get("set-cookie", "").lower()
