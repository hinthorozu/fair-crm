"""Retry tests for mail send operations."""

from unittest.mock import patch
from uuid import UUID, uuid4

from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel


def _operation_events(logs: list) -> list[str]:
    return [entry["event"] for entry in logs]


def _create_smtp_account(client, auth_headers, **overrides):
    payload = {
        "name": "Retry SMTP",
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


def _failed_smtp_test_operation_id(client, auth_headers, recipient: str = "retry-fail@example.com") -> str:
    create = _create_smtp_account(client, auth_headers)
    account_id = create.json()["id"]
    with patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message") as mock_send:
        mock_send.side_effect = SmtpMailDeliveryError(
            "SMTP kimlik doğrulaması başarısız.",
            error_type="SMTPAuthenticationError",
        )
        client.post(
            f"/api/v1/smtp/accounts/{account_id}/test",
            json={"recipient": recipient},
            headers=auth_headers,
        )
    listing = client.get(
        "/api/v1/mail-send-operations",
        params={"status": "failed", "source_type": "smtp_test"},
        headers=auth_headers,
    )
    item = next(row for row in listing.json()["items"] if row["recipient_email"] == recipient)
    return item["id"]


@patch("app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message")
def test_retry_failed_smtp_test_success(mock_send, client, auth_headers):
    operation_id = _failed_smtp_test_operation_id(client, auth_headers, "retry-ok@example.com")

    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["operation"]["status"] == MailSendOperationStatus.SENT
    assert body["operation"]["retry_count"] == 1
    events = _operation_events(body["operation"]["operation_logs"])
    assert "retry_requested" in events
    assert "queued" in events
    assert "sending_started" in events
    assert events[-1] == "sent"
    mock_send.assert_called_once()


@patch("app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message")
def test_retry_failed_smtp_test_stays_failed_on_delivery_error(mock_send, client, auth_headers):
    mock_send.side_effect = SmtpMailDeliveryError(
        "SMTP bağlantı hatası.",
        error_type="SMTPConnectError",
    )
    operation_id = _failed_smtp_test_operation_id(client, auth_headers, "retry-fail2@example.com")

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
    events = _operation_events(body["operation"]["operation_logs"])
    assert events[-1] == "failed"


@patch("app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message")
def test_retry_inactive_smtp_fails(mock_send, client, auth_headers, db_session, organization_id):
    operation_id = _failed_smtp_test_operation_id(client, auth_headers, "retry-inactive@example.com")
    operation = (
        db_session.query(MailSendOperationModel)
        .filter(MailSendOperationModel.id == UUID(operation_id))
        .one()
    )
    account = db_session.get(SmtpAccountModel, operation.smtp_account_id)
    account.is_active = False
    db_session.flush()

    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["operation"]["status"] == MailSendOperationStatus.FAILED
    assert body["operation"]["error_code"] == "InactiveAccount"
    mock_send.assert_not_called()


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_retry_non_failed_operation_rejected(mock_send, client, auth_headers):
    create = _create_smtp_account(client, auth_headers, name="Retry Sent SMTP")
    account_id = create.json()["id"]
    client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "retry-sent@example.com"},
        headers=auth_headers,
    )
    listing = client.get(
        "/api/v1/mail-send-operations",
        params={"status": "sent", "source_type": "smtp_test"},
        headers=auth_headers,
    )
    operation_id = next(
        row["id"] for row in listing.json()["items"] if row["recipient_email"] == "retry-sent@example.com"
    )

    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_retry_other_organization_not_found(client, auth_headers, other_organization_id, user_id):
    from app.integrations.kyrox_core.auth import create_test_token

    operation_id = _failed_smtp_test_operation_id(client, auth_headers, "retry-org@example.com")
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=other_headers,
    )
    assert response.status_code == 404


def test_retry_unsupported_source_type(client, auth_headers, db_session, organization_id):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    service = MailSendOperationService(repository)
    operation_id = service.record_immediate_failure(
        CreateMailSendOperationParams(
            organization_id=organization_id,
            source_type=MailSendSourceType.MANUAL_EMAIL,
            recipient_email="manual@example.com",
            subject="Manual",
            body_text="Manual body",
        ),
        error_code="SendFailed",
        error_message="Send failed",
    )

    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "manual_email" in response.json()["detail"]


def test_retry_denied_without_update_permission(client, auth_headers):
    from app.modules.mail_send_operations.api.dependencies import get_authorization_adapter
    from tests.modules.test_endpoint_permission_enforcement import SelectiveAuthorization

    operation_id = _failed_smtp_test_operation_id(client, auth_headers, "retry-perm@example.com")
    client.app.dependency_overrides[get_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.smtp.update"}
    )
    try:
        response = client.post(
            f"/api/v1/mail-send-operations/{operation_id}/retry",
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_retry_failed_template_test_success(mock_send, client, auth_headers):
    smtp = _create_smtp_account(client, auth_headers, name="Template Retry SMTP")
    template = client.post(
        "/api/v1/mail-templates",
        json={
            "key": f"retry_tpl_{uuid4().hex[:8]}",
            "name": "Retry Template",
            "subject": "Merhaba {{ name }}",
            "body_text": "Test {{ name }}",
            "type": "transactional",
            "language": "tr",
            "is_active": True,
        },
        headers=auth_headers,
    )
    template_id = template.json()["id"]

    with patch(
        "app.modules.mail_templates.application.send_test_mail_template.send_smtp_message",
        side_effect=SmtpMailDeliveryError("fail", error_type="SMTPAuthenticationError"),
    ):
        client.post(
            f"/api/v1/mail-templates/{template_id}/test-email",
            json={
                "to_email": "tpl-retry@example.com",
                "variables": {"name": "Ali"},
                "smtp_account_id": smtp.json()["id"],
            },
            headers=auth_headers,
        )

    listing = client.get(
        "/api/v1/mail-send-operations",
        params={"status": "failed", "source_type": "template_test"},
        headers=auth_headers,
    )
    operation_id = next(
        row["id"] for row in listing.json()["items"] if row["recipient_email"] == "tpl-retry@example.com"
    )

    with patch(
        "app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message"
    ) as retry_send:
        response = client.post(
            f"/api/v1/mail-send-operations/{operation_id}/retry",
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert response.json()["success"] is True
    retry_send.assert_called_once()


@patch("app.modules.mail_send_operations.application.retry_mail_send_operation.send_smtp_message")
def test_retry_failed_template_test_delivery_error(mock_send, client, auth_headers):
    mock_send.side_effect = SmtpMailDeliveryError("fail again", error_type="SMTPAuthenticationError")
    smtp = _create_smtp_account(client, auth_headers, name="Template Retry Fail SMTP")
    template = client.post(
        "/api/v1/mail-templates",
        json={
            "key": f"retry_tpl_fail_{uuid4().hex[:8]}",
            "name": "Retry Template Fail",
            "subject": "Merhaba",
            "body_text": "Test",
            "type": "transactional",
            "language": "tr",
            "is_active": True,
        },
        headers=auth_headers,
    )
    template_id = template.json()["id"]

    with patch(
        "app.modules.mail_templates.application.send_test_mail_template.send_smtp_message",
        side_effect=SmtpMailDeliveryError("fail", error_type="SMTPAuthenticationError"),
    ):
        client.post(
            f"/api/v1/mail-templates/{template_id}/test-email",
            json={
                "to_email": "tpl-retry-fail@example.com",
                "variables": {},
                "smtp_account_id": smtp.json()["id"],
            },
            headers=auth_headers,
        )

    listing = client.get(
        "/api/v1/mail-send-operations",
        params={"status": "failed", "source_type": "template_test"},
        headers=auth_headers,
    )
    operation_id = next(
        row["id"] for row in listing.json()["items"] if row["recipient_email"] == "tpl-retry-fail@example.com"
    )

    response = client.post(
        f"/api/v1/mail-send-operations/{operation_id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["operation"]["status"] == MailSendOperationStatus.FAILED
