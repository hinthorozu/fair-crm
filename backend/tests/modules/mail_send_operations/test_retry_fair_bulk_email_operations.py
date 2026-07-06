"""Retry tests for failed fair bulk email mail send operations."""

from unittest.mock import patch
from uuid import UUID

from app.integrations.kyrox_core.auth import create_test_token
from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from tests.modules.fair_emails.test_process_fair_email_batch import _seed_pending_batch


def _operation_events(body: dict) -> list[str]:
    return [entry["event"] for entry in body["operation"]["operation_logs"]]


def _failed_fair_bulk_operation_id(
    db_session,
    organization_id,
    user_id,
    client,
    auth_headers,
) -> tuple[str, UUID]:
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    with patch(
        "app.modules.fair_emails.application.process_batch.send_smtp_message",
        side_effect=SmtpMailDeliveryError("Authentication failed", error_type="SMTPAuthenticationError"),
    ):
        ProcessFairEmailBatchUseCase(db_session).execute(
            ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
        )
    db_session.expire_all()
    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id, FairEmailOutboxModel.source == "customer")
        .one()
    )
    operation = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id == outbox.mail_send_operation_id)
        .one()
    )
    assert operation.status == MailSendOperationStatus.FAILED
    assert operation.source_type == MailSendSourceType.FAIR_BULK_EMAIL
    return str(operation.id), outbox.id


@patch("app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message")
def test_retry_failed_fair_bulk_email_success(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
    user_id,
):
    operation_id, outbox_id = _failed_fair_bulk_operation_id(
        db_session, organization_id, user_id, client, auth_headers
    )
    before_count = db_session.query(MailSendOperationModel).count()

    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["operation"]["status"] == MailSendOperationStatus.SENT
    assert body["operation"]["retry_count"] == 1
    events = _operation_events(body)
    assert "retry_requested" in events
    assert "queued" in events
    assert "sending_started" in events
    assert events[-1] == "sent"
    mock_send.assert_called_once()

    db_session.expire_all()
    assert db_session.query(MailSendOperationModel).count() == before_count
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
    assert outbox.status == "sent"
    assert outbox.sent_at is not None
    assert outbox.error_message is None


@patch("app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message")
def test_retry_failed_fair_bulk_email_delivery_error(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
    user_id,
):
    mock_send.side_effect = SmtpMailDeliveryError("Connection refused", error_type="SMTPConnectError")
    operation_id, outbox_id = _failed_fair_bulk_operation_id(
        db_session, organization_id, user_id, client, auth_headers
    )

    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["operation"]["status"] == MailSendOperationStatus.FAILED
    assert body["operation"]["retry_count"] == 1
    assert body["operation"]["error_code"] == "SMTPConnectError"
    events = _operation_events(body)
    assert events[-1] == "failed"

    db_session.expire_all()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
    assert outbox.status == "failed"
    assert outbox.error_message == "Connection refused"


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_retry_skipped_fair_bulk_email_rejected(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    from app.modules.contacts.infrastructure.persistence.models import ContactModel
    from tests.conftest_customer_helpers import create_test_customer
    from tests.modules.fair_emails.test_fair_bulk_email_api import (
        _create_contact,
        _create_fair,
        _create_participation,
        _create_smtp,
        _create_template,
    )

    fair_id = _create_fair(client, auth_headers)
    customer = create_test_customer(
        db_session,
        organization_id,
        display_name="Skip Retry Co",
        email="info@skip.com",
    )
    db_session.commit()
    contact_id = _create_contact(client, auth_headers, str(customer.id), email="blocked@skip.com")
    _create_participation(client, auth_headers, fair_id, str(customer.id), primary_contact_id=contact_id)
    template_id = _create_template(client, auth_headers, key=f"skip_retry_{fair_id[:8]}")
    _create_smtp(client, auth_headers)

    contact = db_session.query(ContactModel).filter(ContactModel.id == UUID(contact_id)).one()
    contact.email_allowed = False
    db_session.commit()

    response = client.post(
        f"/api/v1/fairs/{fair_id}/bulk-email/send",
        json={
            "template_id": template_id,
            "recipient_options": {"include_customer_emails": True, "include_contact_emails": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    batch_id = UUID(response.json()["batch_id"])
    skipped = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.batch_id == batch_id,
            MailSendOperationModel.status == MailSendOperationStatus.SKIPPED,
        )
        .one()
    )

    retry_response = client.post(
        f"/api/v1/mail-send-operations/{skipped.id}/retry",
        headers=auth_headers,
    )
    assert retry_response.status_code == 400


@patch("app.modules.fair_emails.application.process_batch.send_smtp_message")
def test_retry_sent_fair_bulk_email_rejected(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(db_session, organization_id, user_id, client, auth_headers)
    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(batch_id=batch_id, organization_id=organization_id)
    )
    db_session.expire_all()
    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.batch_id == batch_id,
            MailSendOperationModel.status == MailSendOperationStatus.SENT,
        )
        .first()
    )
    assert operation is not None

    response = client.post(
        f"/api/v1/mail-send-operations/{operation.id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 400


@patch("app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message")
def test_retry_fair_bulk_email_other_organization_not_found(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
    user_id,
    other_organization_id,
):
    operation_id, _ = _failed_fair_bulk_operation_id(
        db_session, organization_id, user_id, client, auth_headers
    )
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=other_headers,
    )
    assert response.status_code == 404
    mock_send.assert_not_called()


@patch("app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message")
def test_retry_fair_bulk_email_does_not_create_duplicate_operation(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
    user_id,
):
    operation_id, _ = _failed_fair_bulk_operation_id(
        db_session, organization_id, user_id, client, auth_headers
    )
    assert (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id == UUID(operation_id))
        .count()
        == 1
    )

    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    db_session.expire_all()
    assert (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id == UUID(operation_id))
        .count()
        == 1
    )
