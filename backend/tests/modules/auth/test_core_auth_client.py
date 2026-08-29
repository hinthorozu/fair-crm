"""Unit coverage for the thin FAIR CRM -> KYROX Core auth client."""

from __future__ import annotations

import json

import httpx
import pytest

from app.modules.auth.infrastructure.core_auth_client import (
    CoreAuthClient,
    CoreAuthError,
)


def _json_body(request: httpx.Request) -> dict:
    return json.loads(request.content.decode("utf-8"))


def test_signup_forwards_public_contract_and_omits_unselected_slug() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            202,
            json={"message": "Signup accepted. Check your email to activate your account."},
        )

    client = CoreAuthClient(
        base_url="http://core.test",
        transport=httpx.MockTransport(handler),
    )

    result = client.signup(
        organization_name="Acme Turkey",
        email="admin@example.com",
    )

    assert result.message == "Signup accepted. Check your email to activate your account."
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == "/api/v1/auth/signup"
    assert _json_body(request) == {
        "organization_name": "Acme Turkey",
        "email": "admin@example.com",
    }
    assert "authorization" not in request.headers


def test_signup_forwards_selected_organization_slug() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert _json_body(request) == {
            "organization_name": "Acme Turkey",
            "email": "admin@example.com",
            "organization_slug": "acme-turkey",
        }
        return httpx.Response(202, json={"message": "Signup accepted"})

    client = CoreAuthClient(
        base_url="http://core.test",
        transport=httpx.MockTransport(handler),
    )

    assert client.signup(
        organization_name="Acme Turkey",
        email="admin@example.com",
        organization_slug="acme-turkey",
    ).message == "Signup accepted"


@pytest.mark.parametrize(
    ("method_name", "kwargs", "expected_path", "expected_body"),
    [
        (
            "complete_activation",
            {"token": "activation-token", "password": "short-is-forwarded"},
            "/api/v1/auth/activation/complete",
            {"token": "activation-token", "password": "short-is-forwarded"},
        ),
        (
            "forgot_password",
            {"email": "recover@example.com"},
            "/api/v1/auth/password/forgot",
            {"email": "recover@example.com"},
        ),
        (
            "reset_password",
            {"token": "reset-token", "password": "short-is-forwarded"},
            "/api/v1/auth/password/reset",
            {"token": "reset-token", "password": "short-is-forwarded"},
        ),
    ],
)
def test_public_onboarding_methods_are_thin_core_proxies(
    method_name: str,
    kwargs: dict,
    expected_path: str,
    expected_body: dict,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"message": "Accepted by Core"})

    client = CoreAuthClient(
        base_url="http://core.test",
        transport=httpx.MockTransport(handler),
    )

    method = getattr(client, method_name)
    result = method(**kwargs)

    assert result.message == "Accepted by Core"
    assert len(requests) == 1
    assert requests[0].url.path == expected_path
    assert _json_body(requests[0]) == expected_body
    assert "authorization" not in requests[0].headers


def test_change_password_forwards_bearer_token_without_local_credential_logic() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"message": "Password changed. Sign in again."})

    client = CoreAuthClient(
        base_url="http://core.test",
        transport=httpx.MockTransport(handler),
    )

    result = client.change_password(
        access_token="access-token",
        current_password="current-plaintext",
        new_password="short-is-forwarded",
    )

    assert result.message == "Password changed. Sign in again."
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/api/v1/auth/password/change"
    assert request.headers["Authorization"] == "Bearer access-token"
    assert _json_body(request) == {
        "current_password": "current-plaintext",
        "new_password": "short-is-forwarded",
    }


def test_new_auth_methods_preserve_safe_core_4xx_and_hide_5xx_details() -> None:
    responses = iter(
        [
            httpx.Response(422, json={"detail": "Password does not meet policy"}),
            httpx.Response(503, json={"detail": "smtp_password=provider-secret"}),
        ]
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return next(responses)

    client = CoreAuthClient(
        base_url="http://core.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CoreAuthError) as validation_error:
        client.reset_password(token="reset-token", password="weak")
    assert validation_error.value.status_code == 422
    assert validation_error.value.message == "Password does not meet policy"

    with pytest.raises(CoreAuthError) as provider_error:
        client.forgot_password(email="recover@example.com")
    assert provider_error.value.status_code == 503
    assert provider_error.value.message == "Authentication service unavailable"
    assert "provider-secret" not in provider_error.value.message


def test_new_auth_methods_fail_closed_on_malformed_core_success_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = CoreAuthClient(
        base_url="http://core.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CoreAuthError) as exc_info:
        client.complete_activation(token="activation-token", password="password")

    assert exc_info.value.status_code == 502
    assert exc_info.value.message == "Invalid authentication response"
