"""SMTP delivery helper for test mail and future outbound mail."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.value_objects import SmtpEncryptionType

logger = logging.getLogger(__name__)


def _build_message(
    account: SmtpAccount,
    *,
    recipient: str,
    subject: str,
    body: str,
) -> EmailMessage:
    message = EmailMessage()
    if account.from_name:
        message["From"] = f"{account.from_name} <{account.from_email}>"
    else:
        message["From"] = account.from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    return message


def send_smtp_message(
    account: SmtpAccount,
    *,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    if not account.password:
        raise SmtpMailDeliveryError("SMTP password is not configured")

    message = _build_message(account, recipient=recipient, subject=subject, body=body)
    encryption = account.encryption_type
    host = account.host.strip()
    port = account.port
    username = account.username.strip() if account.username else None
    password = account.password

    try:
        if encryption in (SmtpEncryptionType.SSL, SmtpEncryptionType.TLS):
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
            return

        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if encryption == SmtpEncryptionType.STARTTLS:
                context = ssl.create_default_context()
                smtp.starttls(context=context)
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except SmtpMailDeliveryError:
        raise
    except smtplib.SMTPAuthenticationError as exc:
        logger.info(
            "SMTP authentication failed host=%s port=%s account_id=%s",
            host,
            port,
            account.id,
        )
        raise SmtpMailDeliveryError("SMTP authentication failed") from exc
    except smtplib.SMTPException as exc:
        logger.info(
            "SMTP delivery failed host=%s port=%s account_id=%s error=%s",
            host,
            port,
            account.id,
            exc.__class__.__name__,
        )
        raise SmtpMailDeliveryError(f"SMTP delivery failed: {exc}") from exc
    except OSError as exc:
        logger.info(
            "SMTP connection failed host=%s port=%s account_id=%s error=%s",
            host,
            port,
            account.id,
            exc.__class__.__name__,
        )
        raise SmtpMailDeliveryError(f"SMTP connection failed: {exc}") from exc
