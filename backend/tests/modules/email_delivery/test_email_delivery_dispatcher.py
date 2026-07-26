from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_delivery.application.dispatcher import EmailDeliveryDispatcher
from app.modules.email_delivery.application.provider_registry import EmailProviderRegistry
from app.modules.email_delivery.domain.exceptions import UnsupportedProviderError
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.email_delivery.infrastructure.fake_provider import FakeProviderAdapter


def _smtp_account(**overrides) -> EmailAccount:
    now = datetime.now(tz=UTC)
    data = {
        "organization_id": uuid4(),
        "name": "Primary SMTP",
        "from_email": "noreply@example.com",
        "account_type": EmailAccountType.SMTP,
        "now": now,
    }
    data.update(overrides)
    return EmailAccount.create(**data)


def _provider_account(*, provider_key: str = "fake", **overrides) -> EmailAccount:
    now = datetime.now(tz=UTC)
    data = {
        "organization_id": uuid4(),
        "name": "Fake Provider",
        "from_email": "noreply@example.com",
        "account_type": EmailAccountType.PROVIDER,
        "provider_key": provider_key,
        "now": now,
    }
    data.update(overrides)
    return EmailAccount.create(**data)


def _smtp_config(account_id) -> EmailAccountSmtpConfig:
    return EmailAccountSmtpConfig.create(
        email_account_id=account_id,
        host="smtp.example.com",
        port=587,
        username="user",
        password="secret",
        encryption_type="starttls",
    )


def test_smtp_route_calls_smtp_sender():
    account = _smtp_account()
    smtp_config = _smtp_config(account.id)
    smtp_sender = MagicMock()
    smtp_sender.send.return_value = EmailDeliveryResult(
        success=True,
        transport="smtp",
        external_message_id=None,
    )
    dispatcher = EmailDeliveryDispatcher(smtp_sender=smtp_sender)

    result = dispatcher.send(
        account,
        recipient="to@example.com",
        subject="Hello",
        body_html="<p>Hi</p>",
        body_text="Hi",
        smtp_config=smtp_config,
    )

    assert result.success is True
    assert result.transport == "smtp"
    smtp_sender.send.assert_called_once_with(
        account,
        recipient="to@example.com",
        subject="Hello",
        body_html="<p>Hi</p>",
        body_text="Hi",
        smtp_config=smtp_config,
    )


def test_unsupported_provider_raises():
    account = _provider_account(provider_key="not-a-real-provider")
    dispatcher = EmailDeliveryDispatcher()

    with pytest.raises(UnsupportedProviderError) as exc_info:
        dispatcher.send(
            account,
            recipient="to@example.com",
            subject="Hello",
        )

    assert exc_info.value.error_code == "UnsupportedProvider"


def test_fake_provider_adapter_dispatches_successfully():
    account = _provider_account(provider_key="fake")
    registry = EmailProviderRegistry()
    fake = FakeProviderAdapter()
    registry.register(fake)
    dispatcher = EmailDeliveryDispatcher(provider_registry=registry)

    result = dispatcher.send(
        account,
        recipient="to@example.com",
        subject="Hello",
        body_html="<p>Hi</p>",
        body_text="Hi",
    )

    assert result.success is True
    assert result.transport == "provider:fake"
    assert result.external_message_id == "fake-msg-1"
    assert result.provider_status == "accepted"
    assert len(fake.sent) == 1
    assert fake.sent[0]["recipient"] == "to@example.com"
    assert fake.sent[0]["subject"] == "Hello"
