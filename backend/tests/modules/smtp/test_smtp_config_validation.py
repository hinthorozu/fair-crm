import ssl

import pytest

from app.modules.smtp.domain.smtp_config_validation import (
    NONE_ON_465_WARNING,
    SSL_PORT_WARNING,
    SSL_WRONG_VERSION_USER_MESSAGE,
    STARTTLS_PORT_WARNING,
    smtp_config_warnings,
    user_facing_connection_error,
)
from app.modules.smtp.domain.value_objects import SmtpEncryptionType
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message


def test_smtp_config_warning_ssl_with_port_587():
    warnings = smtp_config_warnings(587, SmtpEncryptionType.SSL)
    assert warnings == [SSL_PORT_WARNING]


def test_smtp_config_warning_starttls_with_port_465():
    warnings = smtp_config_warnings(465, SmtpEncryptionType.STARTTLS)
    assert warnings == [STARTTLS_PORT_WARNING]


def test_smtp_config_warning_ssl_with_port_465():
    assert smtp_config_warnings(465, SmtpEncryptionType.SSL) == []


def test_smtp_config_warning_starttls_with_port_587():
    assert smtp_config_warnings(587, SmtpEncryptionType.STARTTLS) == []


def test_smtp_config_warning_none_with_port_465():
    warnings = smtp_config_warnings(465, SmtpEncryptionType.NONE)
    assert warnings == [NONE_ON_465_WARNING]


def test_user_facing_connection_error_maps_wrong_version_number():
    exc = ssl.SSLError("[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1082)")
    assert user_facing_connection_error(exc) == SSL_WRONG_VERSION_USER_MESSAGE


def test_user_facing_connection_error_generic_os_error():
    message = user_facing_connection_error(OSError("Connection refused"))
    assert "WRONG_VERSION_NUMBER" not in message
    assert "Connection refused" not in message


def test_create_smtp_account_includes_ssl_port_warning(client, auth_headers):
    response = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Mismatch SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "password": "secret-password",
            "encryption_type": "ssl",
            "is_default": False,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["config_warnings"] == [SSL_PORT_WARNING]


def test_create_smtp_account_no_warning_for_starttls_587(client, auth_headers):
    response = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Valid SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "password": "secret-password",
            "encryption_type": "starttls",
            "is_default": False,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["config_warnings"] == []


def test_send_test_smtp_mail_maps_ssl_wrong_version_error(client, auth_headers, monkeypatch):
    from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError

    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Test Mail SMTP",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "username": "smtp-user",
            "password": "secret-password",
            "encryption_type": "ssl",
            "is_default": True,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    account_id = create.json()["id"]

    def _raise_ssl_error(account, *, recipient, subject, body):
        _ = (account, recipient, subject, body)
        raise SmtpMailDeliveryError(SSL_WRONG_VERSION_USER_MESSAGE)

    monkeypatch.setattr(
        "app.modules.smtp.application.send_test_smtp_mail.send_smtp_message",
        _raise_ssl_error,
    )

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["message"] == SSL_WRONG_VERSION_USER_MESSAGE
    assert "WRONG_VERSION_NUMBER" not in response.json()["message"]


def test_send_smtp_message_maps_wrong_version_number(monkeypatch):
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.modules.smtp.domain.entities import SmtpAccount
    from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
    from app.modules.smtp.domain.value_objects import SmtpEncryptionType

    account = SmtpAccount(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test",
        from_email="noreply@example.com",
        from_name=None,
        host="smtp.example.com",
        port=587,
        username="user",
        password="secret",
        encryption_type=SmtpEncryptionType.SSL,
        is_default=False,
        is_active=True,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        deleted_at=None,
    )

    class FakeSMTPSSL:
        def __init__(self, *args, **kwargs):
            raise ssl.SSLError("[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1082)")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("app.modules.smtp.infrastructure.smtp_mailer.smtplib.SMTP_SSL", FakeSMTPSSL)

    with pytest.raises(SmtpMailDeliveryError) as exc_info:
        send_smtp_message(
            account,
            recipient="admin@example.com",
            subject="Test",
            body="Body",
        )

    assert exc_info.value.args[0] == SSL_WRONG_VERSION_USER_MESSAGE
