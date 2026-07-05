"""Tests for fair bulk email mail_send_operations integration."""

from unittest.mock import patch
from uuid import UUID

from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from tests.modules.fair_emails.test_fair_bulk_email_api import _setup_fair_with_recipients
from tests.modules.fair_emails.test_process_fair_email_batch import _seed_pending_batch


def _operation_events(operation: MailSendOperationModel) -> list[str]:
    return [entry["event"] for entry in operation.operation_logs]


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_bulk_send_creates_mail_send_operations(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    data = _setup_fair_with_recipients(client, auth_headers, db_session, organization_id)
    response = client.post(
        f"/api/v1/fairs/{data['fair_id']}/bulk-email/send",
        json={
            "template_id": data["template_id"],
            "subject_override": "Fuar daveti",
            "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    batch_id = UUID(response.json()["batch_id"])

    outbox_items = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .all()
    )
    assert len(outbox_items) >= 1
    assert all(item.mail_send_operation_id is not None for item in outbox_items)

    operations = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.batch_id == batch_id,
        )
        .all()
    )
    assert len(operations) == len(outbox_items)
    for operation in operations:
        assert operation.source_type == MailSendSourceType.FAIR_BULK_EMAIL
        assert operation.priority == 99
        assert operation.organization_id == organization_id
        assert operation.fair_id == UUID(data["fair_id"])
        assert operation.customer_id is not None
        assert operation.recipient_email
        assert operation.subject == "Fuar daveti"
        assert operation.smtp_account_id is not None
        assert operation.template_id == UUID(data["template_id"])
        assert operation.status in (
            MailSendOperationStatus.QUEUED,
            MailSendOperationStatus.SENDING,
            MailSendOperationStatus.SENT,
        )
        assert "queued" in _operation_events(operation)


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_process_batch_marks_mail_operations_sent(
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

    db_session.expire_all()
    outbox_items = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .all()
    )
    operation_ids = [item.mail_send_operation_id for item in outbox_items]
    assert all(operation_id is not None for operation_id in operation_ids)

    operations = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id.in_(operation_ids))
        .all()
    )
    assert len(operations) == len(outbox_items)
    for operation in operations:
        assert operation.status == MailSendOperationStatus.SENT
        events = _operation_events(operation)
        assert "queued" in events
        assert "sending_started" in events
        assert "sent" in events
        assert operation.sent_at is not None


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_process_batch_marks_mail_operations_failed(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    mock_send.side_effect = SmtpMailDeliveryError("Authentication failed")
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    db_session.expire_all()
    outbox_items = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .all()
    )
    operation_ids = [item.mail_send_operation_id for item in outbox_items]
    operations = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id.in_(operation_ids))
        .all()
    )
    for operation in operations:
        assert operation.status == MailSendOperationStatus.FAILED
        events = _operation_events(operation)
        assert "queued" in events
        assert "sending_started" in events
        assert "failed" in events
        assert operation.failed_at is not None
        assert operation.error_message == "Authentication failed"


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_process_batch_does_not_create_duplicate_operations(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    use_case = ProcessFairEmailBatchUseCase(db_session)

    use_case.execute(ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id))

    db_session.expire_all()
    outbox_items = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .all()
    )
    operation_ids = [item.mail_send_operation_id for item in outbox_items]
    assert len(operation_ids) == len(set(operation_ids))

    operations = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.batch_id == batch_id)
        .all()
    )
    assert len(operations) == len(outbox_items)

    first_operation = operations[0]
    first_events = _operation_events(first_operation)

    use_case._mail_operation_sync.sync_outbox_sent(
        organization_id,
        outbox_items[0],
        subject=first_operation.subject,
        body_html="<p>test</p>",
        body_text="test",
    )
    db_session.expire_all()
    refreshed = db_session.query(MailSendOperationModel).filter(MailSendOperationModel.id == first_operation.id).one()
    assert _operation_events(refreshed) == first_events
