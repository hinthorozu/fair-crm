"""SMTP delivery helper for test mail and future outbound mail."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any
from uuid import UUID

from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.smtp_error_mapping import map_smtp_exception
from app.modules.smtp.domain.value_objects import SmtpEncryptionType

logger = logging.getLogger(__name__)


def _build_message(
    account: SmtpAccount,
    *,
    recipient: str,
    subject: str,
    body: str,
    body_html: str | None = None,
) -> EmailMessage:
    message = EmailMessage()
    if account.from_name:
        message["From"] = f"{account.from_name} <{account.from_email}>"
    else:
        message["From"] = account.from_email
    message["To"] = recipient
    message["Subject"] = subject
    if body_html:
        message.set_content(body or " ")
        message.add_alternative(body_html, subtype="html")
    else:
        message.set_content(body)
    return message


def _connection_mode(encryption: SmtpEncryptionType) -> str:
    if encryption in (SmtpEncryptionType.SSL, SmtpEncryptionType.TLS):
        return "ssl"
    if encryption == SmtpEncryptionType.STARTTLS:
        return "starttls"
    return "plain"


def _log_debug(event: str, account_id: UUID, **fields: Any) -> None:
    parts = [f"smtp_{event}", f"account_id={account_id}"]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    logger.debug(" ".join(parts))


def _login_if_needed(
    smtp: smtplib.SMTP,
    *,
    username: str | None,
    password: str,
    account_id: UUID,
) -> None:
    if not username:
        _log_debug("login_skipped", account_id, reason="no_username")
        return
    _log_debug("login_start", account_id, username=username)
    try:
        smtp.login(username, password)
    except Exception:
        _log_debug("login_failure", account_id, username=username)
        raise
    _log_debug("login_success", account_id, username=username)


def _send_message(
    smtp: smtplib.SMTP,
    message: EmailMessage,
    *,
    account_id: UUID,
    recipient: str,
) -> None:
    _log_debug("send_message_start", account_id, to_email=recipient)
    try:
        smtp.send_message(message)
    except Exception:
        _log_debug("send_message_failure", account_id, to_email=recipient)
        raise
    _log_debug("send_message_success", account_id, to_email=recipient)


def _raise_delivery_error(exc: BaseException) -> None:
    user_message, error_type, raw_message = map_smtp_exception(exc)
    raise SmtpMailDeliveryError(
        user_message,
        error_type=error_type,
        raw_message=raw_message,
    ) from exc


def send_smtp_message(
    account: SmtpAccount,
    *,
    recipient: str,
    subject: str,
    body: str,
    body_html: str | None = None,
) -> None:
    if not account.password:
        raise SmtpMailDeliveryError(
            "SMTP password is not configured",
            error_type="MissingPassword",
            raw_message="SMTP password is not configured",
        )

    message = _build_message(
        account,
        recipient=recipient,
        subject=subject,
        body=body,
        body_html=body_html,
    )
    encryption = account.encryption_type
    host = account.host.strip()
    port = account.port
    username = account.username.strip() if account.username else None
    password = account.password
    mode = _connection_mode(encryption)

    _log_debug(
        "connection_start",
        account.id,
        host=host,
        port=port,
        encryption_type=encryption.value,
        mode=mode,
        from_email=account.from_email,
        to_email=recipient,
        password_set=True,
    )

    try:
        if encryption in (SmtpEncryptionType.SSL, SmtpEncryptionType.TLS):
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
                _log_debug("connection_opened", account.id, mode="ssl", host=host, port=port)
                _login_if_needed(smtp, username=username, password=password, account_id=account.id)
                _send_message(smtp, message, account_id=account.id, recipient=recipient)
                _log_debug("connection_close", account.id, mode="ssl", host=host, port=port)
            return

        with smtplib.SMTP(host, port, timeout=30) as smtp:
            _log_debug("connection_opened", account.id, mode="plain", host=host, port=port)
            if encryption == SmtpEncryptionType.STARTTLS:
                _log_debug("starttls_start", account.id, host=host, port=port)
                context = ssl.create_default_context()
                smtp.starttls(context=context)
                _log_debug("starttls_success", account.id, host=host, port=port)
            _login_if_needed(smtp, username=username, password=password, account_id=account.id)
            _send_message(smtp, message, account_id=account.id, recipient=recipient)
            _log_debug("connection_close", account.id, mode=mode, host=host, port=port)
    except SmtpMailDeliveryError:
        raise
    except Exception as exc:
        logger.warning(
            "smtp_delivery_failed account_id=%s host=%s port=%s encryption_type=%s "
            "from_email=%s to_email=%s exception_type=%s raw_message=%s",
            account.id,
            host,
            port,
            encryption.value,
            account.from_email,
            recipient,
            type(exc).__name__,
            exc,
        )
        _raise_delivery_error(exc)
