"""Tests for mail send operation worker (Phase 1)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from app.core.config import get_settings
from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import FairBulkEmailMailOperationSync
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    ProcessMailSendOperationsWorker,
)
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
    priority_for_source,
)
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel
from tests.modules.fair_emails.test_fair_bulk_email_api import _setup_fair_with_recipients
from tests.modules.fair_emails.test_process_fair_email_batch import _seed_pending_batch


def _operation_events(logs: list) -> list[str]:
    return [entry["event"] for entry in logs]


def _create_smtp(db_session, organization_id) -> UUID:
    now = datetime.now(timezone.utc)
    account_id = uuid4()
    db_session.add(
        SmtpAccountModel(
            id=account_id,
            organization_id=organization_id,
            name="Worker SMTP",
            from_email="noreply@example.com",
            host="smtp.example.com",
            port=587,
            username="smtp-user",
            password="secret-password",
            encryption_type="starttls",
            is_default=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()
    return account_id


def _create_queued_operation(
    db_session,
    organization_id,
    *,
    source_type=MailSendSourceType.SMTP_TEST,
    recipient_email="worker@example.com",
    priority: int | None = None,
    scheduled_at: datetime | None = None,
    smtp_account_id: UUID | None = None,
) -> MailSendOperationModel:
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    account_id = smtp_account_id or _create_smtp(db_session, organization_id)
    record = repository.create(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=source_type,
            recipient_email=recipient_email,
            subject="Worker test",
            body_text="Body",
            smtp_account_id=account_id,
            scheduled_at=scheduled_at,
        )
    )
    if priority is not None:
        model = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == record.id).one()
        model.priority = priority
        db_session.flush()
    return db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == record.id).one()


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
def test_worker_processes_max_batch_size(mock_send, db_session, organization_id, monkeypatch):
    monkeypatch.setenv("MAIL_WORKER_MAX_BATCH_SIZE", "3")
    get_settings.cache_clear()
    for index in range(5):
        _create_queued_operation(
            db_session,
            organization_id,
            recipient_email=f"batch-{index}@example.com",
        )

    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.picked_count == 3
    assert result.sent_count == 3
    assert mock_send.call_count == 3
    queued_remaining = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.status == MailSendOperationStatus.QUEUED,
        )
        .count()
    )
    assert queued_remaining == 2


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
def test_worker_processes_only_queued_records(mock_send, db_session, organization_id):
    queued = _create_queued_operation(db_session, organization_id, recipient_email="queued@example.com")
    sent = _create_queued_operation(db_session, organization_id, recipient_email="sent@example.com")
    sent.status = MailSendOperationStatus.SENT
    sent.sent_at = datetime.now(timezone.utc)
    failed = _create_queued_operation(db_session, organization_id, recipient_email="failed@example.com")
    failed.status = MailSendOperationStatus.FAILED
    failed.failed_at = datetime.now(timezone.utc)
    cancelled = _create_queued_operation(db_session, organization_id, recipient_email="cancelled@example.com")
    cancelled.status = MailSendOperationStatus.CANCELLED
    cancelled.cancelled_at = datetime.now(timezone.utc)
    db_session.flush()

    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.picked_count == 1
    assert result.sent_count == 1
    assert mock_send.call_count == 1
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == queued.id).one()
    assert refreshed.status == MailSendOperationStatus.SENT
    assert db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == sent.id).one().status == "sent"


def test_worker_skips_consent_skipped_records(db_session, organization_id):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    repository.create_consent_skipped(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.FAIR_BULK_EMAIL,
            recipient_email="skipped@example.com",
            subject="Skipped",
            smtp_account_id=_create_smtp(db_session, organization_id),
        ),
        error_code="consent_blocked",
        error_message="Consent blocked",
    )
    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.picked_count == 0
    skipped = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.recipient_email == "skipped@example.com")
        .one()
    )
    assert skipped.status == MailSendOperationStatus.SKIPPED


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
def test_worker_respects_priority_order(mock_send, db_session, organization_id, monkeypatch):
    monkeypatch.setenv("MAIL_WORKER_MAX_BATCH_SIZE", "1")
    get_settings.cache_clear()
    _create_queued_operation(
        db_session,
        organization_id,
        source_type=MailSendSourceType.FAIR_BULK_EMAIL,
        recipient_email="bulk@example.com",
        priority=99,
    )
    _create_queued_operation(
        db_session,
        organization_id,
        source_type=MailSendSourceType.SMTP_TEST,
        recipient_email="smtp@example.com",
        priority=40,
    )

    ProcessMailSendOperationsWorker(db_session).run()
    assert mock_send.call_args.kwargs["recipient"] == "smtp@example.com"


def test_fair_bulk_email_priority_is_low():
    assert priority_for_source(MailSendSourceType.FAIR_BULK_EMAIL) == 99
    assert priority_for_source(MailSendSourceType.SMTP_TEST) < priority_for_source(MailSendSourceType.FAIR_BULK_EMAIL)


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
def test_worker_marks_stuck_sending_as_failed(mock_send, db_session, organization_id, monkeypatch):
    monkeypatch.setenv("MAIL_SENDING_TIMEOUT_MINUTES", "15")
    get_settings.cache_clear()
    stuck = _create_queued_operation(db_session, organization_id, recipient_email="stuck@example.com")
    stuck.status = MailSendOperationStatus.SENDING
    stuck.sending_started_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    db_session.flush()

    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.recovered_stuck_count == 1
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == stuck.id).one()
    assert refreshed.status == MailSendOperationStatus.FAILED
    assert refreshed.error_code == "sending_timeout"
    events = _operation_events(refreshed.operation_logs)
    assert "sending_timeout" in events
    assert events[-1] == "failed"
    mock_send.assert_not_called()


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
def test_worker_continues_after_single_failure(mock_send, db_session, organization_id):
    mock_send.side_effect = [
        SmtpMailDeliveryError("fail", error_type="SMTPConnectError"),
        None,
    ]
    _create_queued_operation(db_session, organization_id, recipient_email="fail@example.com")
    _create_queued_operation(db_session, organization_id, recipient_email="ok@example.com")

    result = ProcessMailSendOperationsWorker(db_session).run()
    assert result.sent_count == 1
    assert result.failed_count == 1
    assert mock_send.call_count == 2


@patch("app.modules.mail_send_operations.application.mail_send_operation_dispatcher.send_smtp_message")
def test_worker_writes_controlled_operation_logs(mock_send, db_session, organization_id):
    operation = _create_queued_operation(db_session, organization_id, recipient_email="logs@example.com")
    ProcessMailSendOperationsWorker(db_session).run()
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    events = _operation_events(refreshed.operation_logs)
    assert "picked_by_worker" in events
    assert "sending_started" in events
    assert "sent" in events
    assert events.count("picked_by_worker") == 1


def test_append_operation_log_once_avoids_duplicate_events(db_session, organization_id):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    operation = _create_queued_operation(db_session, organization_id, recipient_email="dedupe@example.com")
    repository.append_operation_log_once(
        organization_id,
        operation.id,
        event="picked_by_worker",
        message="Worker tarafından seçildi",
    )
    repository.append_operation_log_once(
        organization_id,
        operation.id,
        event="picked_by_worker",
        message="Worker tarafından seçildi",
    )
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == operation.id).one()
    assert _operation_events(refreshed.operation_logs).count("picked_by_worker") == 1


def test_fair_bulk_duplicate_operation_is_not_created(db_session, organization_id, user_id, client, auth_headers):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    batch = SqlAlchemyFairEmailBatchRepository(db_session).get_batch(organization_id, batch_id)
    assert batch is not None
    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .first()
    )
    sync = FairBulkEmailMailOperationSync(db_session)
    sync.ensure_operations_for_batch(
        organization_id=organization_id,
        batch=batch,
        default_subject="Fuar daveti",
    )
    first_operation_id = outbox.mail_send_operation_id
    sync.ensure_operations_for_batch(
        organization_id=organization_id,
        batch=batch,
        default_subject="Fuar daveti",
    )
    db_session.expire_all()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox.id).one()
    assert outbox.mail_send_operation_id == first_operation_id
    count = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.batch_id == batch_id)
        .count()
    )
    assert count == (
        db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.batch_id == batch_id).count()
    )


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_smtp_test_existing_behavior_unchanged(mock_send, client, auth_headers, db_session, organization_id):
    from tests.modules.smtp.test_smtp_test_mail_api import _create_account

    create = _create_account(client, auth_headers)
    account_id = create.json()["id"]
    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "unchanged@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.SMTP_TEST,
        )
        .one()
    )
    assert operation.status == MailSendOperationStatus.SENT
    assert _operation_events(operation.operation_logs) == ["queued", "sending_started", "sent"]


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_template_test_existing_behavior_unchanged(mock_send, client, auth_headers, db_session, organization_id):
    from tests.modules.smtp.test_smtp_test_mail_api import _create_account

    smtp = _create_account(client, auth_headers, name="Template Worker SMTP")
    template = client.post(
        "/api/v1/mail-templates",
        json={
            "key": f"worker_tpl_{uuid4().hex[:8]}",
            "name": "Worker Template",
            "subject": "Merhaba",
            "body_text": "Test",
            "type": "transactional",
            "language": "tr",
            "is_active": True,
        },
        headers=auth_headers,
    )
    response = client.post(
        f"/api/v1/mail-templates/{template.json()['id']}/test-email",
        json={
            "to_email": "tpl-worker@example.com",
            "variables": {},
            "smtp_account_id": smtp.json()["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.TEMPLATE_TEST,
        )
        .one()
    )
    assert operation.status == MailSendOperationStatus.SENT


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_fair_bulk_existing_behavior_unchanged(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )
    operations = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.batch_id == batch_id)
        .all()
    )
    assert operations
    assert all(item.status == MailSendOperationStatus.SENT for item in operations)


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_fair_bulk_customer_activity_unchanged(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    from app.modules.activities.infrastructure.persistence.models import ActivityModel

    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    response = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/send",
        json={
            "template_id": data["template_id"],
            "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    activities = db_session.query(ActivityModel).all()
    fair_bulk_activities = [
        activity
        for activity in activities
        if (activity.metadata_json or {}).get("source") == "fair_bulk_email"
    ]
    assert len(fair_bulk_activities) >= 1
