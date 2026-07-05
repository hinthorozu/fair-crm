import logging
import smtplib
import socket
import ssl
from socket import gaierror
from unittest.mock import patch

import pytest

from app.modules.smtp.application.smtp_test_debug import smtp_debug_response_enabled
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.smtp_error_mapping import (
    AUTHENTICATION_USER_MESSAGE,
    CONNECTION_REFUSED_USER_MESSAGE,
    SSL_WRONG_VERSION_USER_MESSAGE,
    TIMEOUT_USER_MESSAGE,
    map_smtp_exception,
)
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message


def test_map_smtp_authentication_error():
    exc = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
    message, error_type, raw = map_smtp_exception(exc)
    assert message == AUTHENTICATION_USER_MESSAGE
    assert error_type == "SMTPAuthenticationError"
    assert "Authentication failed" in raw


def test_map_smtp_timeout_error():
    message, error_type, _ = map_smtp_exception(TimeoutError("timed out"))
    assert message == TIMEOUT_USER_MESSAGE
    assert error_type == "TimeoutError"


def test_map_ssl_wrong_version_error():
    exc = ssl.SSLError("[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1082)")
    message, error_type, raw = map_smtp_exception(exc)
    assert message == SSL_WRONG_VERSION_USER_MESSAGE
    assert error_type == "SSLError"
    assert "WRONG_VERSION_NUMBER" in raw


def test_map_connection_refused_error():
    message, error_type, _ = map_smtp_exception(ConnectionRefusedError(111, "Connection refused"))
    assert message == CONNECTION_REFUSED_USER_MESSAGE
    assert error_type == "ConnectionRefusedError"


def test_map_dns_error():
    message, error_type, _ = map_smtp_exception(gaierror(8, "nodename nor servname provided"))
    assert error_type == "gaierror"
    assert "çözümlenemedi" in message


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_test_mail_failure_returns_structured_response_without_debug(mock_send, client, auth_headers):
    mock_send.side_effect = SmtpMailDeliveryError(
        AUTHENTICATION_USER_MESSAGE,
        error_type="SMTPAuthenticationError",
        raw_message="535 Authentication failed",
    )
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Debug SMTP",
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
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["message"] == AUTHENTICATION_USER_MESSAGE
    assert "password" not in body
    assert body.get("debug_error_type") is None
    assert body.get("debug_error_message") is None


@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_test_mail_failure_includes_debug_fields_when_enabled(
    mock_send,
    client,
    auth_headers,
    monkeypatch,
):
    monkeypatch.setenv("FAIR_CRM_SMTP_DEBUG_RESPONSE", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    mock_send.side_effect = SmtpMailDeliveryError(
        AUTHENTICATION_USER_MESSAGE,
        error_type="SMTPAuthenticationError",
        raw_message="535 Authentication failed",
    )
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Debug SMTP Enabled",
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
    account_id = create.json()["id"]

    response = client.post(
        f"/api/v1/smtp/accounts/{account_id}/test",
        json={"recipient": "admin@example.com"},
        headers=auth_headers,
    )
    body = response.json()
    assert body["debug_error_type"] == "SMTPAuthenticationError"
    assert body["debug_error_message"] == "535 Authentication failed"
    assert body["smtp_host"] == "smtp.example.com"
    assert body["smtp_port"] == 587
    assert body["encryption_type"] == "starttls"
    get_settings.cache_clear()


def test_smtp_test_failure_logs_do_not_include_password(caplog, monkeypatch):
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.modules.smtp.application.smtp_test_debug import log_smtp_test_mail_failure
    from app.modules.smtp.domain.entities import SmtpAccount
    from app.modules.smtp.domain.value_objects import SmtpEncryptionType

    caplog.set_level(logging.WARNING)
    account = SmtpAccount(
        id=uuid4(),
        organization_id=uuid4(),
        name="Secret SMTP",
        from_email="noreply@example.com",
        from_name=None,
        host="smtp.example.com",
        port=587,
        username="smtp-user",
        password="super-secret-password",
        encryption_type=SmtpEncryptionType.STARTTLS,
        is_default=False,
        is_active=True,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        deleted_at=None,
    )
    exc = SmtpMailDeliveryError(
        AUTHENTICATION_USER_MESSAGE,
        error_type="SMTPAuthenticationError",
        raw_message="535 Authentication failed",
    )

    log_smtp_test_mail_failure(
        account=account,
        organization_id=account.organization_id,
        recipient="admin@example.com",
        exc=exc,
    )

    log_text = caplog.text.lower()
    assert "super-secret-password" not in log_text
    assert "password_set=true" in log_text


def test_send_smtp_message_does_not_log_password(monkeypatch, caplog):
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.modules.smtp.domain.entities import SmtpAccount
    from app.modules.smtp.domain.value_objects import SmtpEncryptionType

    caplog.set_level(logging.DEBUG)
    account = SmtpAccount(
        id=uuid4(),
        organization_id=uuid4(),
        name="Secret SMTP",
        from_email="noreply@example.com",
        from_name=None,
        host="smtp.example.com",
        port=587,
        username="smtp-user",
        password="super-secret-password",
        encryption_type=SmtpEncryptionType.STARTTLS,
        is_default=False,
        is_active=True,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        deleted_at=None,
    )

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self, context=None):
            return (220, b"Ready")

        def login(self, username, password):
            _ = password
            raise smtplib.SMTPAuthenticationError(535, b"Authentication failed")

        def send_message(self, message):
            return {}

    monkeypatch.setattr("app.modules.smtp.infrastructure.smtp_mailer.smtplib.SMTP", FakeSMTP)

    with pytest.raises(SmtpMailDeliveryError):
        send_smtp_message(
            account,
            recipient="admin@example.com",
            subject="Test",
            body="Body",
        )

    assert "super-secret-password" not in caplog.text.lower()


def test_smtp_debug_response_disabled_in_production(monkeypatch):
    monkeypatch.setenv("FAIR_CRM_SMTP_DEBUG_RESPONSE", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FAIR_CRM_DEV_BYPASS_CORE", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert smtp_debug_response_enabled() is False
    get_settings.cache_clear()
