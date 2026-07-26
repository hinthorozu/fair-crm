"""Persistence tests for mail_send_operations provider result fields."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.email_delivery.infrastructure.fake_provider import FakeProviderAdapter
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    ProcessMailSendOperationsWorker,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from tests.modules.mail_send_operations.test_mail_send_operations_worker import (
    _create_queued_operation,
)


def test_mark_sent_persists_provider_result_fields(db_session, organization_id):
    repo = SqlAlchemyMailSendOperationRepository(db_session)
    created = repo.create(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.MANUAL_TASK_MAIL,
            recipient_email="recipient@example.com",
            subject="Provider result persistence",
            body_text="body",
            max_retry_count=3,
        )
    )
    assert created.external_message_id is None
    assert created.provider_status is None

    sent = repo.mark_sent(
        organization_id,
        created.id,
        external_message_id="msg-abc-123",
        provider_status="accepted",
    )
    db_session.commit()

    loaded = repo.get_by_id(organization_id, created.id)
    assert loaded is not None
    assert loaded.status == MailSendOperationStatus.SENT
    assert loaded.sent_at is not None
    assert loaded.external_message_id == "msg-abc-123"
    assert loaded.provider_status == "accepted"
    assert sent.external_message_id == "msg-abc-123"
    assert sent.provider_status == "accepted"


def test_smtp_mark_sent_keeps_provider_fields_null(db_session, organization_id):
    repo = SqlAlchemyMailSendOperationRepository(db_session)
    created = repo.create(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.SMTP_TEST,
            recipient_email="smtp@example.com",
            subject="SMTP null provider fields",
            body_text="body",
            email_account_id=uuid4(),
        )
    )
    sent = repo.mark_sent(organization_id, created.id)
    db_session.commit()

    loaded = repo.get_by_id(organization_id, created.id)
    assert loaded is not None
    assert loaded.status == MailSendOperationStatus.SENT
    assert loaded.external_message_id is None
    assert loaded.provider_status is None
    assert sent.external_message_id is None
    assert sent.provider_status is None


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
)
def test_worker_persists_fake_provider_result_on_mark_sent(mock_send, db_session, organization_id):
    fake = FakeProviderAdapter(
        external_message_id="test-provider-message-id",
        provider_status="accepted",
    )
    # Adapter result flows through dispatcher unchanged into worker mark_sent.
    mock_send.return_value = fake.send(
        type("Account", (), {})(),
        recipient="provider-ok@example.com",
        subject="Worker test",
    )

    operation = _create_queued_operation(
        db_session,
        organization_id,
        source_type=MailSendSourceType.MANUAL_TASK_MAIL,
        recipient_email="provider-ok@example.com",
    )

    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.sent_count == 1

    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert refreshed.status == MailSendOperationStatus.SENT
    assert refreshed.external_message_id == "test-provider-message-id"
    assert refreshed.provider_status == "accepted"


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_worker_smtp_success_keeps_provider_fields_null(mock_send, db_session, organization_id):
    operation = _create_queued_operation(
        db_session,
        organization_id,
        source_type=MailSendSourceType.MANUAL_TASK_MAIL,
        recipient_email="smtp-null@example.com",
    )

    ProcessMailSendOperationsWorker(db_session).run()
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert refreshed.status == MailSendOperationStatus.SENT
    assert refreshed.external_message_id is None
    assert refreshed.provider_status is None


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send",
)
def test_worker_provider_failure_keeps_provider_fields_null(mock_send, db_session, organization_id):
    mock_send.side_effect = SmtpMailDeliveryError("provider down", error_type="401")
    operation = _create_queued_operation(
        db_session,
        organization_id,
        source_type=MailSendSourceType.MANUAL_TASK_MAIL,
        recipient_email="provider-fail@example.com",
    )

    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.failed_count == 1

    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert refreshed.status == MailSendOperationStatus.FAILED
    assert refreshed.external_message_id is None
    assert refreshed.provider_status is None


def test_prepare_for_retry_clears_provider_result_fields(db_session, organization_id):
    repo = SqlAlchemyMailSendOperationRepository(db_session)
    created = repo.create(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.MANUAL_TASK_MAIL,
            recipient_email="retry-clear@example.com",
            subject="clear fields",
            body_text="body",
            max_retry_count=3,
        )
    )
    repo.mark_sent(
        organization_id,
        created.id,
        external_message_id="old-msg",
        provider_status="accepted",
    )
    # Force failed so prepare_for_retry is allowed
    model = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == created.id).one()
    model.status = MailSendOperationStatus.FAILED
    db_session.flush()

    retried = repo.prepare_for_retry(organization_id, created.id)
    assert retried.external_message_id is None
    assert retried.provider_status is None
    loaded = repo.get_by_id(organization_id, created.id)
    assert loaded is not None
    assert loaded.external_message_id is None
    assert loaded.provider_status is None


def test_requeue_for_auto_retry_clears_provider_result_fields(db_session, organization_id):
    repo = SqlAlchemyMailSendOperationRepository(db_session)
    created = repo.create(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.MANUAL_TASK_MAIL,
            recipient_email="auto-retry-clear@example.com",
            subject="clear fields",
            body_text="body",
            max_retry_count=3,
        )
    )
    repo.mark_sent(
        organization_id,
        created.id,
        external_message_id="old-msg",
        provider_status="accepted",
    )

    requed = repo.requeue_for_auto_retry(organization_id, created.id)
    assert requed.status == MailSendOperationStatus.QUEUED
    assert requed.external_message_id is None
    assert requed.provider_status is None
    loaded = repo.get_by_id(organization_id, created.id)
    assert loaded is not None
    assert loaded.external_message_id is None
    assert loaded.provider_status is None
