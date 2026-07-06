"""SMTP timeout settings loaded from application config."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class SmtpTimeoutSettings:
    connect_timeout_seconds: int
    send_timeout_seconds: int
    mail_operation_timeout_seconds: int


def get_smtp_timeout_settings() -> SmtpTimeoutSettings:
    settings = get_settings()
    return SmtpTimeoutSettings(
        connect_timeout_seconds=settings.smtp_connect_timeout_seconds,
        send_timeout_seconds=settings.smtp_send_timeout_seconds,
        mail_operation_timeout_seconds=settings.mail_operation_timeout_seconds,
    )
