"""Unit tests for SMTP mailer timeout behavior."""

import socket
import smtplib
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.smtp_timeout_errors import (
    SMTP_CONNECT_TIMEOUT_CODE,
    SMTP_TIMEOUT_CODE,
)
from app.modules.smtp.domain.value_objects import SmtpEncryptionType
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message
from app.modules.smtp.infrastructure.smtp_timeout_settings import get_smtp_timeout_settings


def _account(**overrides) -> SmtpAccount:
    data = {
        "id": uuid4(),
        "organization_id": uuid4(),
        "name": "Timeout SMTP",
        "from_email": "noreply@example.com",
        "from_name": None,
        "host": "smtp.example.com",
        "port": 587,
        "username": "smtp-user",
        "password": "secret-password",
        "encryption_type": SmtpEncryptionType.STARTTLS,
        "is_default": True,
        "is_active": True,
        "deleted_at": None,
        "created_at": None,
        "updated_at": None,
    }
    data.update(overrides)
    return SmtpAccount(**data)


def test_smtp_timeout_settings_defaults(monkeypatch):
    monkeypatch.delenv("SMTP_CONNECT_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("SMTP_SEND_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("MAIL_OPERATION_TIMEOUT_SECONDS", raising=False)
    get_settings.cache_clear()
    settings = get_smtp_timeout_settings()
    assert settings.connect_timeout_seconds == 10
    assert settings.send_timeout_seconds == 30
    assert settings.mail_operation_timeout_seconds == 60


def test_smtp_timeout_settings_from_env(monkeypatch):
    monkeypatch.setenv("SMTP_CONNECT_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("SMTP_SEND_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("MAIL_OPERATION_TIMEOUT_SECONDS", "45")
    get_settings.cache_clear()
    settings = get_smtp_timeout_settings()
    assert settings.connect_timeout_seconds == 7
    assert settings.send_timeout_seconds == 15
    assert settings.mail_operation_timeout_seconds == 45
    get_settings.cache_clear()


def test_send_smtp_message_connect_timeout(monkeypatch):
    class FakeSMTP:
        def __init__(self, host, port, timeout=10):
            assert timeout == 10
            raise socket.timeout("connect timed out")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setenv("SMTP_CONNECT_TIMEOUT_SECONDS", "10")
    get_settings.cache_clear()
    monkeypatch.setattr("app.modules.smtp.infrastructure.smtp_mailer.smtplib.SMTP", FakeSMTP)

    with pytest.raises(SmtpMailDeliveryError) as exc_info:
        send_smtp_message(
            _account(),
            recipient="admin@example.com",
            subject="Test",
            body="Body",
        )

    assert exc_info.value.error_type == SMTP_CONNECT_TIMEOUT_CODE
    assert "bağlantı" in exc_info.value.args[0].lower()


def test_send_smtp_message_send_timeout(monkeypatch):
    class FakeSMTP:
        def __init__(self, host, port, timeout=10):
            self.sock = self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def settimeout(self, value):
            return None

        def starttls(self, context=None):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            raise socket.timeout("send timed out")

    fake = FakeSMTP
    monkeypatch.setenv("SMTP_SEND_TIMEOUT_SECONDS", "30")
    get_settings.cache_clear()
    monkeypatch.setattr("app.modules.smtp.infrastructure.smtp_mailer.smtplib.SMTP", fake)

    with pytest.raises(SmtpMailDeliveryError) as exc_info:
        send_smtp_message(
            _account(),
            recipient="admin@example.com",
            subject="Test",
            body="Body",
        )

    assert exc_info.value.error_type == SMTP_TIMEOUT_CODE
    assert "gönderimi" in exc_info.value.args[0].lower()


def test_send_smtp_message_applies_send_timeout_on_socket(monkeypatch):
    captured: dict[str, int | None] = {"send_timeout": None}

    class FakeSMTP:
        def __init__(self, host, port, timeout=10):
            self.sock = self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def settimeout(self, value):
            captured["send_timeout"] = value

        def starttls(self, context=None):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            return None

    monkeypatch.setenv("SMTP_SEND_TIMEOUT_SECONDS", "25")
    get_settings.cache_clear()
    monkeypatch.setattr("app.modules.smtp.infrastructure.smtp_mailer.smtplib.SMTP", FakeSMTP)

    send_smtp_message(
        _account(),
        recipient="admin@example.com",
        subject="Test",
        body="Body",
    )
    assert captured["send_timeout"] == 25


def test_send_smtp_message_operation_timeout(monkeypatch):
    class SlowSMTP:
        def __init__(self, host, port, timeout=10):
            self.sock = self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def settimeout(self, value):
            return None

        def starttls(self, context=None):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            import time

            time.sleep(2)

    monkeypatch.setenv("MAIL_OPERATION_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()
    monkeypatch.setattr("app.modules.smtp.infrastructure.smtp_mailer.smtplib.SMTP", SlowSMTP)

    with pytest.raises(SmtpMailDeliveryError) as exc_info:
        send_smtp_message(
            _account(),
            recipient="admin@example.com",
            subject="Test",
            body="Body",
        )

    assert exc_info.value.error_type == SMTP_TIMEOUT_CODE


def test_send_smtp_message_ssl_connect_timeout(monkeypatch):
    class FakeSMTPSSL:
        def __init__(self, host, port, context=None, timeout=10):
            raise smtplib.SMTPConnectError(421, b"connect timeout")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.modules.smtp.infrastructure.smtp_mailer.smtplib.SMTP_SSL", FakeSMTPSSL)

    with pytest.raises(SmtpMailDeliveryError) as exc_info:
        send_smtp_message(
            _account(encryption_type=SmtpEncryptionType.SSL, port=465),
            recipient="admin@example.com",
            subject="Test",
            body="Body",
        )

    assert exc_info.value.error_type == SMTP_CONNECT_TIMEOUT_CODE
