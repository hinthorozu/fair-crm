"""Mail send operations infrastructure tests."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.domain.exceptions import MissingOrganizationIdError
from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError


def _operation_events(logs: list) -> list[str]:
    return [entry["event"] for entry in logs]


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_smtp_test_mail_creates_sent_operation(mock_send, client, auth_headers, db_session, organization_id):
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Ops SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "username": "smtp-user",
            "password": "secret-password",
            "encryption_type": "starttls",
            "is_default": True,
            "is_active": True,
        },
        headers=auth_headers,
    )
    account_id = create.json()["id"]
    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.SMTP_TEST,
        )
        .one()
    )
    assert operation.organization_id == organization_id
    assert operation.status == MailSendOperationStatus.SENT
    assert operation.recipient_email == "admin@example.com"
    assert operation.smtp_account_id is not None
    assert operation.subject == "FAIR CRM SMTP Test"
    assert operation.priority == 40
    assert operation.sent_at is not None
    assert _operation_events(operation.operation_logs) == ["queued", "sending_started", "sent"]


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_smtp_test_mail_creates_failed_operation(mock_send, client, auth_headers, db_session, organization_id):
    mock_send.side_effect = SmtpMailDeliveryError(
        "SMTP kimlik doğrulaması başarısız.",
        error_type="SMTPAuthenticationError",
    )
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Ops SMTP Fail",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "username": "smtp-user",
            "password": "secret-password",
            "encryption_type": "starttls",
            "is_default": True,
            "is_active": True,
        },
        headers=auth_headers,
    )
    account_id = create.json()["id"]
    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
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
    assert operation.error_code == "SMTPAuthenticationError"
    assert operation.failed_at is not None
    assert _operation_events(operation.operation_logs) == ["queued", "sending_started", "failed"]


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_smtp_test_mail_inactive_account_creates_immediate_failure(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Inactive SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "username": "smtp-user",
            "password": "secret-password",
            "encryption_type": "starttls",
            "is_default": True,
            "is_active": False,
        },
        headers=auth_headers,
    )
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
    assert operation.status == MailSendOperationStatus.FAILED
    assert operation.error_code == "InactiveAccount"
    assert str(operation.smtp_account_id) == account_id
    assert operation.priority == 40
    assert _operation_events(operation.operation_logs) == ["failed"]


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_template_test_mail_creates_sent_operation(
    mock_send,
    client,
    auth_headers,
    db_session,
    organization_id,
):
    smtp = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Template SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "username": "smtp-user",
            "password": "secret-password",
            "encryption_type": "starttls",
            "is_default": True,
            "is_active": True,
        },
        headers=auth_headers,
    )
    template = client.post(
        "/api/v1/mail-templates",
        json={
            "key": f"ops_test_{uuid4().hex[:8]}",
            "name": "Ops Template",
            "subject": "Merhaba {{ customer_name }}",
            "body_text": "Test body",
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
            "to_email": "tester@example.com",
            "variables": {"customer_name": "Ali"},
            "smtp_account_id": smtp.json()["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    operation = (
        db_session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.source_type == MailSendSourceType.TEMPLATE_TEST,
        )
        .one()
    )
    assert operation.status == MailSendOperationStatus.SENT
    assert operation.template_id is not None
    assert operation.priority == 40
    assert _operation_events(operation.operation_logs) == ["queued", "sending_started", "sent"]


def test_create_mail_send_operation_requires_organization_id(db_session):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    service = MailSendOperationService(repository)
    with pytest.raises(MissingOrganizationIdError):
        service.create_mail_send_operation(
            CreateMailSendOperationParams(
                organization_id=None,  # type: ignore[arg-type]
                source_type=MailSendSourceType.SMTP_TEST,
                recipient_email="a@example.com",
                subject="Test",
            )
        )


def test_list_by_organization_requires_organization_id(db_session):
    repository = SqlAlchemyMailSendOperationRepository(db_session)
    with pytest.raises(MissingOrganizationIdError):
        repository.list_by_organization(None)  # type: ignore[arg-type]


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_list_mail_send_operations_returns_smtp_test_record(
    mock_send,
    client,
    auth_headers,
    organization_id,
):
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "List API SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "username": "smtp-user",
            "password": "secret-password",
            "encryption_type": "starttls",
            "is_default": True,
            "is_active": True,
        },
        headers=auth_headers,
    )
    account_id = create.json()["id"]
    send = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "list-api@example.com"},
        headers=auth_headers,
    )
    assert send.status_code == 200

    response = client.get("/api/v1/mail-send-operations", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    item = next(row for row in body["items"] if row["recipient_email"] == "list-api@example.com")
    assert item["source_type"] == MailSendSourceType.SMTP_TEST
    assert item["source_type_label"] == "SMTP Test"
    assert item["status"] == MailSendOperationStatus.SENT
    assert item["status_label"] == "Gönderildi"
    assert item["priority"] == 40
    assert item["smtp_account_id"] == account_id
    assert item["smtp_account_name"] == "List API SMTP"
    assert _operation_events(item["operation_logs"]) == ["queued", "sending_started", "sent"]


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_list_mail_send_operations_filters_by_status(
    mock_send,
    client,
    auth_headers,
):
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Filter SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "username": "smtp-user",
            "password": "secret-password",
            "encryption_type": "starttls",
            "is_default": True,
            "is_active": True,
        },
        headers=auth_headers,
    )
    account_id = create.json()["id"]
    client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "filter@example.com"},
        headers=auth_headers,
    )

    response = client.get(
        "/api/v1/mail-send-operations",
        params={"status": "sent", "source_type": "smtp_test"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert all(item["status"] == "sent" for item in response.json()["items"])
    assert all(item["source_type"] == "smtp_test" for item in response.json()["items"])


def test_list_mail_send_operations_denied_without_read_permission(client, auth_headers):
    from app.modules.mail_send_operations.api.dependencies import get_authorization_adapter
    from tests.modules.test_endpoint_permission_enforcement import SelectiveAuthorization

    client.app.dependency_overrides[get_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.smtp.read"}
    )
    try:
        response = client.get("/api/v1/mail-send-operations", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_authorization_adapter, None)
