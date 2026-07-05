"""SMTP test mail API tests."""

from unittest.mock import patch

from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message


def _create_account(client, auth_headers):
    return client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Test Mail SMTP",
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


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_send_test_smtp_mail_success(mock_send, client, auth_headers):
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


def test_send_test_smtp_mail_invalid_recipient(client, auth_headers):
    create = _create_account(client, auth_headers)
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "not-an-email"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message", side_effect=Exception("boom"))
def test_send_test_smtp_mail_delivery_error(mock_send, client, auth_headers):
    from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError

    mock_send.side_effect = SmtpMailDeliveryError("SMTP authentication failed")
    create = _create_account(client, auth_headers)
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "authentication failed" in response.json()["detail"].lower()
