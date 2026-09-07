"""OL07-07 certification for already-started SMTP/provider handoff semantics."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest

from app.modules.email_accounts.domain.entities import EmailAccount
from app.modules.email_accounts.domain.error_policy import (
    DeliveryErrorAction,
    ProviderErrorPolicy,
)
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_delivery.application.dispatcher import EmailDeliveryDispatcher
from app.modules.email_delivery.application.provider_registry import EmailProviderRegistry
from app.modules.email_delivery.domain.exceptions import (
    PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE,
    EmailDeliveryError,
)
from app.modules.email_delivery.domain.retryability import is_retryable_delivery_error
from app.modules.email_delivery.infrastructure.mailersend_adapter import MailerSendAdapter
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    ProcessMailSendOperationsWorker,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.smtp_timeout_errors import SMTP_HANDOFF_UNCERTAIN_CODE


def _provider_account() -> EmailAccount:
    return EmailAccount.create(
        organization_id=uuid4(),
        name="MailerSend OL07-07",
        from_email="noreply@example.com",
        account_type=EmailAccountType.PROVIDER,
        provider_key="mailersend",
        now=datetime.now(tz=UTC),
    )


def _provider_config() -> dict[str, str]:
    return {
        "api_token": "tok_ol07",
        "from_email": "noreply@example.com",
        "from_name": "FAIR",
    }


def test_mailersend_connect_timeout_remains_pre_handoff_retryable():
    def transport(method, url, headers=None, json=None):
        request = httpx.Request(method, url)
        raise httpx.ConnectTimeout("connect timed out", request=request)

    adapter = MailerSendAdapter(transport=transport)

    with pytest.raises(EmailDeliveryError) as exc_info:
        adapter.send(
            _provider_account(),
            recipient="to@example.com",
            subject="Connect timeout",
            provider_config=_provider_config(),
        )

    assert exc_info.value.error_code == "TimeoutError"
    assert exc_info.value.retryable is True


def test_mailersend_read_timeout_after_handoff_is_uncertain_and_not_retryable():
    def transport(method, url, headers=None, json=None):
        request = httpx.Request(method, url)
        raise httpx.ReadTimeout("response timed out", request=request)

    adapter = MailerSendAdapter(transport=transport)

    with pytest.raises(EmailDeliveryError) as exc_info:
        adapter.send(
            _provider_account(),
            recipient="to@example.com",
            subject="Read timeout",
            provider_config=_provider_config(),
        )

    assert exc_info.value.error_code == PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE
    assert exc_info.value.retryable is False
    assert "duplicate" in str(exc_info.value).lower()


def test_provider_policy_cannot_reenable_auto_retry_for_uncertain_handoff():
    adapter = MagicMock()
    adapter.provider_key = "mailersend"
    adapter.send.side_effect = EmailDeliveryError(
        "provider result unknown",
        error_code=PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE,
        transport="provider:mailersend",
        retryable=False,
    )
    registry = EmailProviderRegistry()
    registry.register(adapter)
    dispatcher = EmailDeliveryDispatcher(provider_registry=registry)
    policy = ProviderErrorPolicy.from_dict(
        {
            "groups": [
                {
                    "category": "DELIVERY_ERROR",
                    "identifiers": [PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE],
                    "action": DeliveryErrorAction.AUTO_RETRY.value,
                }
            ]
        }
    )

    with pytest.raises(EmailDeliveryError) as exc_info:
        dispatcher.send(
            _provider_account(),
            recipient="to@example.com",
            subject="No duplicate retry",
            provider_config=_provider_config(),
            error_policy=policy,
        )

    assert exc_info.value.error_code == PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE
    assert exc_info.value.policy_action == DeliveryErrorAction.AUTO_RETRY.value
    assert exc_info.value.retryable is False


@pytest.mark.parametrize(
    "error_code",
    [
        PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE,
        SMTP_HANDOFF_UNCERTAIN_CODE,
        "sending_timeout",
    ],
)
def test_uncertain_inflight_error_codes_are_never_auto_retryable(error_code):
    assert is_retryable_delivery_error(error_code) is False


class _Repository:
    def __init__(self, claimed):
        self.claimed = claimed
        self.auto_retry = []

    def try_claim_queued_operation(self, organization_id, operation_id, *, now):
        assert organization_id == self.claimed.organization_id
        assert operation_id == self.claimed.id
        return self.claimed

    def set_auto_retry_pending(self, organization_id, operation_id, *, enabled):
        self.auto_retry.append((organization_id, operation_id, enabled))


class _MailService:
    def __init__(self):
        self.failed = []
        self.sending = []

    def mark_worker_sending(self, organization_id, operation_id):
        self.sending.append((organization_id, operation_id))

    def mark_failed(
        self,
        organization_id,
        operation_id,
        *,
        error_code,
        error_message,
        provider_status=None,
    ):
        self.failed.append(
            (organization_id, operation_id, error_code, error_message, provider_status)
        )


class _Dispatcher:
    def dispatch(self, operation):
        raise SmtpMailDeliveryError(
            "provider acceptance is unknown",
            error_type=PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE,
            retryable=False,
        )


def test_worker_terminalizes_uncertain_handoff_without_auto_retry():
    claimed = SimpleNamespace(
        id=uuid4(),
        organization_id=uuid4(),
        source_type=MailSendSourceType.MANUAL_EMAIL,
        status=MailSendOperationStatus.SENDING,
    )
    worker = object.__new__(ProcessMailSendOperationsWorker)
    worker._repository = _Repository(claimed)
    worker._mail_service = _MailService()
    worker._dispatcher = _Dispatcher()

    outcome = worker._process_candidate(claimed, now=datetime.now(tz=UTC))

    assert outcome == "failed"
    assert worker._repository.auto_retry == [
        (claimed.organization_id, claimed.id, False),
    ]
    assert worker._mail_service.failed == [
        (
            claimed.organization_id,
            claimed.id,
            PROVIDER_HANDOFF_UNCERTAIN_ERROR_CODE,
            "provider acceptance is unknown",
            None,
        )
    ]
