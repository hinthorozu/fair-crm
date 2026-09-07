"""OL07-07 durable mail handoff checkpoint regression coverage."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.mail_send_operations.application.mail_send_operation_dispatcher import (
    MailSendOperationDispatcher,
)
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType


def _generic_operation():
    return SimpleNamespace(
        id=uuid4(),
        organization_id=uuid4(),
        source_type=MailSendSourceType.SMTP_TEST,
        recipient_email="durable-handoff@example.com",
        customer_id=None,
        email_account_id=uuid4(),
        subject="OL07-07 durable handoff",
        body_text="Body",
        body_html=None,
    )


def test_dispatch_commits_claimed_sending_state_before_external_handoff():
    session = MagicMock()
    dispatcher = MailSendOperationDispatcher(session)
    dispatcher._consent_policy = MagicMock()
    dispatcher._delivery = MagicMock()
    operation = _generic_operation()

    def _send(**kwargs):
        assert session.commit.call_count == 1
        return EmailDeliveryResult(success=True, transport="smtp")

    dispatcher._delivery.send.side_effect = _send

    result = dispatcher.dispatch(operation)

    assert result.success is True
    session.commit.assert_called_once_with()
    dispatcher._delivery.send.assert_called_once()


def test_dispatch_does_not_touch_provider_when_durable_checkpoint_commit_fails():
    session = MagicMock()
    session.commit.side_effect = RuntimeError("database commit failed")
    dispatcher = MailSendOperationDispatcher(session)
    dispatcher._consent_policy = MagicMock()
    dispatcher._delivery = MagicMock()
    operation = _generic_operation()

    with pytest.raises(RuntimeError, match="database commit failed"):
        dispatcher.dispatch(operation)

    dispatcher._delivery.send.assert_not_called()
