"""Integration tests for SMTP timeout handling across mail flows."""

from unittest.mock import patch
from uuid import UUID, uuid4

from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.smtp_timeout_errors import SMTP_TIMEOUT_CODE
from tests.modules.fair_emails.test_process_fair_email_batch import _seed_pending_batch


def _operation_events(logs: list) -> list[str]:
    return [entry["event"] for entry in logs]


def _create_smtp_account(client, auth_headers, **overrides):
    payload = {
        "name": "Timeout SMTP",
        "from_email": "noreply@example.com",
        "host": "smtp.example.com",
        "port": 587,
        "username": "smtp-user",
        "password": "secret-password",
        "encryption_type": "starttls",
        "is_default": True,
        "is_active": True,
    }
    payload.update(overrides)
    return client.post("/api/v1/smtp/accounts", json=payload, headers=auth_headers)


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_smtp_test_mail_timeout_records_failed_operation(mock_send, client, auth_headers, db_session, organization_id):
    mock_send.side_effect = SmtpMailDeliveryError(
        "SMTP gönderimi zaman aşımına uğradı.",
        error_type=SMTP_TIMEOUT_CODE,
        raw_message="send timed out",
    )
    create = _create_smtp_account(client, auth_headers)
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "timeout@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 400

    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.SMTP_TEST,
        )
        .one()
    )
    assert operation.status == MailSendOperationStatus.FAILED
    assert operation.error_code == SMTP_TIMEOUT_CODE
    events = _operation_events(operation.operation_logs)
    assert events == ["queued", "sending_started", SMTP_TIMEOUT_CODE, "failed"]


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_template_test_mail_timeout_records_failed_operation(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    mock_send.side_effect = SmtpMailDeliveryError(
        "SMTP bağlantısı zaman aşımına uğradı.",
        error_type="smtp_connect_timeout",
        raw_message="connect timed out",
    )
    smtp = _create_smtp_account(client, auth_headers, name="Template Timeout SMTP")
    template = client.post(
        "/api/v1/mail-templates",
        json={
            "key": f"timeout_tpl_{uuid4().hex[:8]}",
            "name": "Timeout Template",
            "subject": "Merhaba",
            "body_text": "Test",
            "type": "transactional",
            "language": "tr",
            "is_active": True,
        },
        headers=auth_headers,
    )
    template_id = template.json()["id"]

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={
            "to_email": "tpl-timeout@example.com",
            "variables": {},
            "smtp_account_id": smtp.json()["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 400

    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.TEMPLATE_TEST,
        )
        .one()
    )
    assert operation.status == MailSendOperationStatus.FAILED
    assert operation.error_code == "smtp_connect_timeout"
    events = _operation_events(operation.operation_logs)
    assert "smtp_connect_timeout" in events
    assert events[-1] == "failed"


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_fair_bulk_timeout_fails_single_outbox_and_continues_batch(
    mock_send,
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    call_count = {"value": 0}

    def side_effect(*args, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise SmtpMailDeliveryError(
                "SMTP gönderimi zaman aşımına uğradı.",
                error_type=SMTP_TIMEOUT_CODE,
                raw_message="send timed out",
            )
        return None

    mock_send.side_effect = side_effect

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )

    db_session.expire_all()
    outbox_items = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .order_by(FairEmailOutboxModel.created_at.asc())
        .all()
    )
    assert len(outbox_items) == 2
    statuses = {item.status for item in outbox_items}
    assert "failed" in statuses
    assert "sent" in statuses

    failed_outbox = next(item for item in outbox_items if item.status == "failed")
    sent_outbox = next(item for item in outbox_items if item.status == "sent")
    assert failed_outbox.error_message is not None
    assert sent_outbox.sent_at is not None

    failed_operation = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id == failed_outbox.mail_send_operation_id)
        .one()
    )
    sent_operation = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id == sent_outbox.mail_send_operation_id)
        .one()
    )
    assert failed_operation.status == MailSendOperationStatus.FAILED
    assert failed_operation.error_code == SMTP_TIMEOUT_CODE
    assert SMTP_TIMEOUT_CODE in _operation_events(failed_operation.operation_logs)
    assert sent_operation.status == MailSendOperationStatus.SENT
    assert mock_send.call_count == 2
