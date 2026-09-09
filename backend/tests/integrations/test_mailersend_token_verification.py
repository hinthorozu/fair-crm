from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app.integrations.mailersend.token_verification import (
    OUTCOME_INVALID,
    OUTCOME_NOT_PROVEN_INVALID,
    OUTCOME_UNKNOWN,
    MailerSendExactSecretVerifier,
)


@pytest.mark.parametrize(
    ("status_code", "outcome", "evidence_code"),
    [
        (401, OUTCOME_INVALID, "mailersend_exact_secret_http_401"),
        (200, OUTCOME_NOT_PROVEN_INVALID, "mailersend_exact_secret_http_200"),
        (403, OUTCOME_NOT_PROVEN_INVALID, "mailersend_exact_secret_http_403"),
        (429, OUTCOME_UNKNOWN, "mailersend_exact_secret_http_429"),
        (500, OUTCOME_UNKNOWN, "mailersend_exact_secret_http_5xx"),
        (503, OUTCOME_UNKNOWN, "mailersend_exact_secret_http_5xx"),
        (418, OUTCOME_UNKNOWN, "mailersend_exact_secret_unexpected_status"),
    ],
)
def test_exact_secret_verifier_classifies_only_bounded_http_evidence(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    outcome: str,
    evidence_code: str,
) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            _ = (exc_type, exc, tb)

        def get(self, url: str, *, headers: dict[str, str], params: dict[str, int]):
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return SimpleNamespace(status_code=status_code)

    monkeypatch.setattr(
        "app.integrations.mailersend.token_verification.httpx.Client",
        FakeClient,
    )

    result = MailerSendExactSecretVerifier(base_url="https://mailersend.example/").verify(
        "exact-secret"
    )

    assert result.outcome == outcome
    assert result.evidence_code == evidence_code
    assert captured == {
        "timeout": 10.0,
        "url": "https://mailersend.example/v1/token",
        "headers": {
            "Authorization": "Bearer exact-secret",
            "Accept": "application/json",
        },
        "params": {"limit": 10},
    }
    assert "exact-secret" not in repr(result)


def test_exact_secret_verifier_fails_closed_on_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingClient:
        def __init__(self, *, timeout: float) -> None:
            _ = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            _ = (exc_type, exc, tb)

        def get(self, url: str, *, headers: dict[str, str], params: dict[str, int]):
            _ = (headers, params)
            request = httpx.Request("GET", url)
            raise httpx.RequestError("provider unavailable", request=request)

    monkeypatch.setattr(
        "app.integrations.mailersend.token_verification.httpx.Client",
        FailingClient,
    )

    result = MailerSendExactSecretVerifier().verify("exact-secret")

    assert result.outcome == OUTCOME_UNKNOWN
    assert result.evidence_code == "mailersend_exact_secret_transport_error"
    assert "exact-secret" not in repr(result)


def test_exact_secret_verifier_rejects_missing_secret_without_network() -> None:
    with pytest.raises(ValueError, match="required"):
        MailerSendExactSecretVerifier().verify("   ")
