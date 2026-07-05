"""Mail template test email API tests."""

from uuid import uuid4

from unittest.mock import patch

from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError

TEST_EMAIL_OPENAPI_PATH = "/api/v1/mail-templates/{template_id}/test-email"


def test_test_email_route_registered_in_openapi(client):
    openapi = client.app.openapi()
    assert TEST_EMAIL_OPENAPI_PATH in openapi["paths"]
    post = openapi["paths"][TEST_EMAIL_OPENAPI_PATH]["post"]
    assert post["tags"] == ["mail-templates"]
    assert "SendTestMailTemplateRequest" in str(post.get("requestBody", {}))


def test_test_email_route_not_starlette_404(client, auth_headers):
    """Unregistered routes return {"detail":"Not Found"} without hitting use case."""
    response = client.post(
        f"/api/v1/mail-templates/{uuid4()}/test-email",
        json={"to_email": "test@example.com", "variables": {"name": "Ada"}},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] != "Not Found"


def _mail_template_payload(**overrides):
    payload = {
        "name": "Welcome Email",
        "key": "welcome_email",
        "subject": "Hello {{ name }}",
        "body_html": "<p>Hello {{ name }}</p>",
        "body_text": "Hello {{ name }}",
    }
    payload.update(overrides)
    return payload


def _create_template(client, auth_headers, **overrides):
    return client.post(
        "/api/v1/mail-templates",
        json=_mail_template_payload(**overrides),
        headers=auth_headers,
    )


def _create_smtp_account(client, auth_headers, **overrides):
    payload = {
        "name": "Primary SMTP",
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


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_send_test_mail_template_success(mock_send, client, auth_headers):
    smtp = _create_smtp_account(client, auth_headers)
    assert smtp.status_code == 201
    template = _create_template(client, auth_headers, key="test_send_ok")
    assert template.status_code == 201
    template_id = template.json()["id"]

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={
            "to_email": "test@example.com",
            "variables": {"name": "Ada"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "password" not in body
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["recipient"] == "test@example.com"
    assert mock_send.call_args.kwargs["subject"] == "Hello Ada"
    assert mock_send.call_args.kwargs["body_html"] == "<p>Hello Ada</p>"


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_send_test_mail_template_subject_override(mock_send, client, auth_headers):
    smtp = _create_smtp_account(client, auth_headers)
    assert smtp.status_code == 201
    template = _create_template(client, auth_headers, key="test_send_subject_override")
    template_id = template.json()["id"]

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={
            "to_email": "test@example.com",
            "variables": {"name": "Ada"},
            "subject_override": "Özel test konusu",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["subject"] == "Özel test konusu"
    assert mock_send.call_args.kwargs["body_html"] == "<p>Hello Ada</p>"


def test_send_test_mail_template_denied_without_permission(client, auth_headers):
    from app.modules.mail_templates.api.dependencies import (
        get_authorization_adapter as get_mail_templates_authorization_adapter,
    )
    from tests.modules.test_endpoint_permission_enforcement import SelectiveAuthorization

    template = _create_template(client, auth_headers, key="test_send_denied")
    template_id = template.json()["id"]
    client.app.dependency_overrides[get_mail_templates_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.mail_templates.test_send"}
    )
    try:
        response = client.post(
            f"/api/v1/mail-templates/{template_id}/test-email",
            json={"to_email": "test@example.com", "variables": {"name": "Ada"}},
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_mail_templates_authorization_adapter, None)


def test_send_test_mail_template_without_default_smtp(client, auth_headers):
    template = _create_template(client, auth_headers, key="test_send_no_smtp")
    template_id = template.json()["id"]

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={"to_email": "test@example.com", "variables": {"name": "Ada"}},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "varsayılan smtp" in response.json()["detail"].lower()


def test_send_test_mail_template_inactive_template_blocked(client, auth_headers):
    _create_smtp_account(client, auth_headers)
    template = _create_template(client, auth_headers, key="test_send_inactive", is_active=False)
    template_id = template.json()["id"]

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={"to_email": "test@example.com", "variables": {"name": "Ada"}},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "pasif" in response.json()["detail"].lower()


def test_send_test_mail_template_inactive_smtp_blocked(client, auth_headers):
    smtp = _create_smtp_account(client, auth_headers, is_active=False)
    template = _create_template(client, auth_headers, key="test_send_inactive_smtp")
    template_id = template.json()["id"]

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={
            "to_email": "test@example.com",
            "variables": {"name": "Ada"},
            "smtp_account_id": smtp.json()["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "pasif" in response.json()["message"].lower()


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_send_test_mail_template_other_org_smtp_not_allowed(mock_send, client, auth_headers, other_organization_id, user_id):
    from app.integrations.kyrox_core.auth import create_test_token

    smtp = _create_smtp_account(client, auth_headers)
    template = _create_template(client, auth_headers, key="test_send_org_guard")
    template_id = template.json()["id"]
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={
            "to_email": "test@example.com",
            "variables": {"name": "Ada"},
            "smtp_account_id": smtp.json()["id"],
        },
        headers=other_headers,
    )
    assert response.status_code == 404
    mock_send.assert_not_called()


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_send_test_mail_template_render_error(mock_send, client, auth_headers):
    _create_smtp_account(client, auth_headers)
    template = _create_template(client, auth_headers, key="test_send_render_error")
    template_id = template.json()["id"]

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={"to_email": "test@example.com", "variables": {}},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "render" in response.json()["detail"].lower()
    mock_send.assert_not_called()


@patch("app.modules.mail_templates.application.send_test_mail_template.send_smtp_message")
def test_send_test_mail_template_missing_password_safe_message(mock_send, client, auth_headers):
    _create_smtp_account(client, auth_headers)
    template = _create_template(client, auth_headers, key="test_send_missing_password")
    template_id = template.json()["id"]
    mock_send.side_effect = SmtpMailDeliveryError(
        "SMTP password is not configured",
        error_type="MissingPassword",
        raw_message="SMTP password is not configured",
    )

    response = client.post(
        f"/api/v1/mail-templates/{template_id}/test-email",
        json={"to_email": "test@example.com", "variables": {"name": "Ada"}},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "şifre" in response.json()["message"].lower()
    assert "password" not in response.json()["message"].lower()
