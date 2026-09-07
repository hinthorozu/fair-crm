"""OL07-07 durable mail handoff checkpoint regression coverage."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.email_delivery.domain.retryability import is_retryable_delivery_error
from app.modules.mail_send_operations.application.mail_send_operation_dispatcher import (
    HANDOFF_CHECKPOINT_COMMIT_FAILED_ERROR_CODE,
    MailSendOperationDispatcher,
)
from app.modules.mail_send_operations.domain.value_objects import MailSendSourceType
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError


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

    with pytest.raises(SmtpMailDeliveryError) as exc_info:
        dispatcher.dispatch(operation)

    assert exc_info.value.error_type == HANDOFF_CHECKPOINT_COMMIT_FAILED_ERROR_CODE
    assert exc_info.value.retryable is True
    assert exc_info.value.raw_message == "database commit failed"
    assert is_retryable_delivery_error(HANDOFF_CHECKPOINT_COMMIT_FAILED_ERROR_CODE) is True
    session.rollback.assert_called_once_with()
    dispatcher._delivery.send.assert_not_called()


def test_dispatch_recovers_real_sqlalchemy_session_after_checkpoint_commit_failure(test_engine):
    session_factory = sessionmaker(bind=test_engine)
    session = session_factory()
    dispatcher = MailSendOperationDispatcher(session)
    dispatcher._consent_policy = MagicMock()
    dispatcher._delivery = MagicMock()
    operation = _generic_operation()

    # Start a real SQLAlchemy transaction. Raising from the engine commit event
    # leaves Session inactive/prepared until rollback() is performed.
    session.execute(text("SELECT 1"))
    failure_state = {"raised": False}

    def _fail_checkpoint_commit(_connection):
        if failure_state["raised"]:
            return
        failure_state["raised"] = True
        raise OperationalError(
            "COMMIT",
            {},
            RuntimeError("forced checkpoint commit failure"),
        )

    event.listen(test_engine, "commit", _fail_checkpoint_commit)
    try:
        with pytest.raises(SmtpMailDeliveryError) as exc_info:
            dispatcher.dispatch(operation)

        assert exc_info.value.error_type == HANDOFF_CHECKPOINT_COMMIT_FAILED_ERROR_CODE
        assert exc_info.value.retryable is True
        assert is_retryable_delivery_error(HANDOFF_CHECKPOINT_COMMIT_FAILED_ERROR_CODE) is True
        dispatcher._delivery.send.assert_not_called()

        # The dispatcher must recover the same Session before the worker tries to
        # persist failure/retry bookkeeping. A query here proves it is reusable.
        assert session.is_active is True
        assert session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        event.remove(test_engine, "commit", _fail_checkpoint_commit)
        session.close()
