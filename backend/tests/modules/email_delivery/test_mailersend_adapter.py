"""MailerSend adapter + dispatcher policy tests (HTTP mocked)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest

from app.modules.email_accounts.domain.entities import EmailAccount
from app.modules.email_accounts.domain.error_policy import (
    AccountErrorAction,
    DeliveryErrorAction,
    MessageErrorAction,
    ProviderErrorPolicy,
)
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_delivery.application.dispatcher import EmailDeliveryDispatcher
from app.modules.email_delivery.application.provider_registry import EmailProviderRegistry
from app.modules.email_delivery.domain.exceptions import (
    EmailDeliveryError,
    ProviderMessageSkippedError,
    UnsupportedProviderError,
)
from app.modules.email_delivery.infrastructure.mailersend_adapter import MailerSendAdapter


def _provider_account(**overrides) -> EmailAccount:
    now = datetime.now(tz=UTC)
    data = {
        "organization_id": uuid4(),
        "name": "MailerSend Prod",
        "from_email": "noreply@example.com",
        "account_type": EmailAccountType.PROVIDER,
        "provider_key": "mailersend",
        "now": now,
    }
    data.update(overrides)
    return EmailAccount.create(**data)


def _policy() -> ProviderErrorPolicy:
    return ProviderErrorPolicy.from_dict(
        {
            "groups": [
                {
                    "category": "ACCOUNT_ERROR",
                    "identifiers": ["401", "403"],
                    "action": AccountErrorAction.DEACTIVATE_AND_FAIL.value,
                },
                {
                    "category": "DELIVERY_ERROR",
                    "identifiers": ["429", "503"],
                    "action": DeliveryErrorAction.AUTO_RETRY.value,
                },
                {
                    "category": "MESSAGE_ERROR",
                    "identifiers": ["422"],
                    "action": MessageErrorAction.SKIP.value,
                },
            ]
        }
    )


def test_mailersend_success_captures_external_message_id():
    def transport(method, url, headers=None, json=None):
        assert method == "POST"
        assert "Bearer tok_123" in headers["Authorization"]
        assert json["from"]["email"] == "from@example.com"
        assert json["to"][0]["email"] == "to@example.com"
        return httpx.Response(
            202,
            headers={"x-message-id": "ms-abc-1"},
            request=httpx.Request("POST", url),
        )

    adapter = MailerSendAdapter(transport=transport)
    result = adapter.send(
        _provider_account(),
        recipient="to@example.com",
        subject="Hi",
        body_html="<p>Hi</p>",
        body_text="Hi",
        provider_config={
            "api_token": "tok_123",
            "from_email": "from@example.com",
            "from_name": "FAIR",
        },
    )
    assert result.success is True
    assert result.external_message_id == "ms-abc-1"
    assert result.provider_status == "accepted"
    assert result.transport == "provider:mailersend"


def test_mailersend_success_without_x_message_id_stays_accepted():
    def transport(method, url, headers=None, json=None):
        return httpx.Response(
            202,
            headers={},
            request=httpx.Request("POST", url),
        )

    adapter = MailerSendAdapter(transport=transport)
    result = adapter.send(
        _provider_account(),
        recipient="to@example.com",
        subject="Hi",
        body_html="<p>Hi</p>",
        body_text="Hi",
        provider_config={
            "api_token": "tok_123",
            "from_email": "from@example.com",
            "from_name": "FAIR",
        },
    )
    assert result.success is True
    assert result.external_message_id is None
    assert result.provider_status == "accepted"
    assert result.transport == "provider:mailersend"


def test_mailersend_auth_error_identifier_is_status():
    def transport(method, url, headers=None, json=None):
        return httpx.Response(
            401,
            json={"message": "Unauthenticated"},
            request=httpx.Request("POST", url),
        )

    adapter = MailerSendAdapter(transport=transport)
    with pytest.raises(EmailDeliveryError) as exc_info:
        adapter.send(
            _provider_account(),
            recipient="to@example.com",
            subject="Hi",
            provider_config={
                "api_token": "bad",
                "from_email": "from@example.com",
                "from_name": "FAIR",
            },
        )
    assert exc_info.value.error_code == "401"


def test_dispatcher_applies_retry_and_deactivate_and_skip():
    adapter = MagicMock()
    adapter.provider_key = "mailersend"
    registry = EmailProviderRegistry()
    registry.register(adapter)
    deactivated = []

    dispatcher = EmailDeliveryDispatcher(
        provider_registry=registry,
        deactivate_account=lambda account: deactivated.append(account.id),
    )
    account = _provider_account()
    policy = _policy()

    adapter.send.side_effect = EmailDeliveryError("nope", error_code="429")
    with pytest.raises(EmailDeliveryError) as retry_exc:
        dispatcher.send(
            account,
            recipient="to@example.com",
            subject="Hi",
            provider_config={"api_token": "x", "from_email": "a@b.com", "from_name": "n"},
            error_policy=policy,
        )
    assert retry_exc.value.retryable is True
    assert retry_exc.value.policy_action == DeliveryErrorAction.AUTO_RETRY.value

    adapter.send.side_effect = EmailDeliveryError("auth", error_code="401")
    with pytest.raises(EmailDeliveryError) as account_exc:
        dispatcher.send(
            account,
            recipient="to@example.com",
            subject="Hi",
            provider_config={"api_token": "x", "from_email": "a@b.com", "from_name": "n"},
            error_policy=policy,
        )
    assert account_exc.value.retryable is False
    assert deactivated == [account.id]

    adapter.send.side_effect = EmailDeliveryError("bad msg", error_code="422")
    with pytest.raises(ProviderMessageSkippedError):
        dispatcher.send(
            account,
            recipient="to@example.com",
            subject="Hi",
            provider_config={"api_token": "x", "from_email": "a@b.com", "from_name": "n"},
            error_policy=policy,
        )

    adapter.send.side_effect = EmailDeliveryError("weird", error_code="999")
    with pytest.raises(EmailDeliveryError) as unknown_exc:
        dispatcher.send(
            account,
            recipient="to@example.com",
            subject="Hi",
            provider_config={"api_token": "x", "from_email": "a@b.com", "from_name": "n"},
            error_policy=policy,
        )
    assert unknown_exc.value.retryable is False


def test_default_registry_includes_mailersend_not_unknown():
    from app.modules.email_delivery.application.provider_registry import (
        create_default_provider_registry,
    )

    registry = create_default_provider_registry()
    assert registry.get("mailersend") is not None
    with pytest.raises(UnsupportedProviderError):
        registry.require("sendgrid")
