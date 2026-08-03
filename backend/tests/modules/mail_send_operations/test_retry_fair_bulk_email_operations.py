"""Retry tests for failed fair bulk email mail send operations."""

from unittest.mock import patch

from app.modules.email_delivery.domain.results import EmailDeliveryResult
from uuid import UUID, uuid4

from app.integrations.kyrox_core.auth import create_test_token
from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
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
        "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryService.send",
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


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryService.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
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
    assert body["operation"]["status"] == MailSendOperationStatus.QUEUED
    assert body["operation"]["retry_count"] == 1
    events = _operation_events(body)
    assert "retry_requested" in events
    assert "queued" in events
    assert events[-1] == "queued"
    mock_send.assert_not_called()

    db_session.expire_all()
    assert db_session.query(MailSendOperationModel).count() == before_count
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
    assert outbox.status == "queued"
    assert outbox.sent_at is None
    assert outbox.error_message is None


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryService.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
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
    assert body["success"] is True
    assert body["operation"]["status"] == MailSendOperationStatus.QUEUED
    assert body["operation"]["retry_count"] == 1
    assert body["operation"]["error_code"] is None
    events = _operation_events(body)
    assert events[-1] == "queued"
    mock_send.assert_not_called()

    db_session.expire_all()
    outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
    assert outbox.status == "queued"
    assert outbox.error_message is None


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryService.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
def test_retry_skipped_fair_bulk_email_rejected(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    """Skipped MSO (e.g. consent) must not be retryable — seed skipped row directly."""
    from app.modules.mail_send_operations.application.mail_send_operation_service import (
        MailSendOperationService,
    )
    from app.shared.consent import CONSENT_ERROR_CODE

    service = MailSendOperationService(SqlAlchemyMailSendOperationRepository(db_session))
    skipped = service.create_consent_skipped_operation(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.FAIR_BULK_EMAIL,
            recipient_email="blocked@skip.com",
            subject="Skip retry",
            body_text="body",
            batch_id=uuid4(),
            max_retry_count=3,
        ),
        error_code=CONSENT_ERROR_CODE,
        error_message="Contact email consent disabled",
    )
    db_session.flush()

    retry_response = client.post(
        f"/api/v1/mail-send-operations/{skipped.id}/retry",
        headers=auth_headers,
    )
    assert retry_response.status_code == 400
    mock_send.assert_not_called()


@patch("app.modules.email_delivery.application.email_delivery_service.EmailDeliveryDispatcher.send")
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


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryService.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
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


@patch(
    "app.modules.email_delivery.application.email_delivery_service.EmailDeliveryService.send",
    return_value=EmailDeliveryResult(success=True, transport="smtp"),
)
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
