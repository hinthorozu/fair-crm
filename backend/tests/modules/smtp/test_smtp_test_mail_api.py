"""SMTP test mail API tests."""

from unittest.mock import patch

from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError


def _operation_events(logs: list) -> list[str]:
    return [entry["event"] for entry in logs]


def _create_account(client, auth_headers, **overrides):
    payload = {
        "name": "Test Mail SMTP",
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
def test_send_test_smtp_mail_success(mock_send, client, auth_headers, db_session, organization_id):
    create = _create_account(client, auth_headers)
    assert create.status_code == 201
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "password" not in body
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["recipient"] == "admin@example.com"

    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.SMTP_TEST,
        )
        .one()
    )
    assert operation.organization_id == organization_id
    assert operation.source_type == MailSendSourceType.SMTP_TEST
    assert operation.priority == 40
    assert operation.status == MailSendOperationStatus.SENT
    assert operation.recipient_email == "admin@example.com"
    assert str(operation.smtp_account_id) == account_id
    assert operation.subject == "FAIR CRM SMTP Test"
    assert operation.error_code is None
    assert operation.error_message is None
    assert operation.sent_at is not None
    assert _operation_events(operation.operation_logs) == ["queued", "sending_started", "sent"]


def test_send_test_smtp_mail_invalid_recipient(client, auth_headers):
    create = _create_account(client, auth_headers)
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "not-an-email"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_send_test_smtp_mail_delivery_error(mock_send, client, auth_headers, db_session, organization_id):
    mock_send.side_effect = SmtpMailDeliveryError(
        "SMTP kimlik doğrulaması başarısız. Kullanıcı adı veya şifreyi kontrol edin.",
        error_type="SMTPAuthenticationError",
        raw_message="535 Authentication failed",
    )
    create = _create_account(client, auth_headers)
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "kimlik doğrulaması" in response.json()["message"].lower()

    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.SMTP_TEST,
        )
        .one()
    )
    assert operation.status == MailSendOperationStatus.FAILED
    assert operation.priority == 40
    assert operation.error_code == "SMTPAuthenticationError"
    assert operation.failed_at is not None
    assert _operation_events(operation.operation_logs) == ["queued", "sending_started", "failed"]


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_send_test_smtp_mail_inactive_account_creates_failed_operation(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    create = _create_account(client, auth_headers, is_active=False)
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["success"] is False
    mock_send.assert_not_called()

    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.SMTP_TEST,
        )
        .one()
    )
    assert operation.organization_id == organization_id
    assert operation.status == MailSendOperationStatus.FAILED
    assert operation.error_code == "InactiveAccount"
    assert str(operation.smtp_account_id) == account_id
    assert _operation_events(operation.operation_logs) == ["failed"]
