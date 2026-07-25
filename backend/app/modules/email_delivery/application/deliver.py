"""Shared helper to send via EmailDeliveryDispatcher while preserving SmtpMailDeliveryError."""

from __future__ import annotations

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_delivery.application.dispatcher import EmailDeliveryDispatcher
from app.modules.email_delivery.domain.exceptions import EmailDeliveryError, UnsupportedProviderError
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.infrastructure.persistence.mappers import smtp_account_to_email_parts


def deliver_with_dispatcher(
    account: EmailAccount,
    *,
    recipient: str,
    subject: str,
    body_text: str | None = None,
    body_html: str | None = None,
    smtp_config: EmailAccountSmtpConfig | None = None,
    dispatcher: EmailDeliveryDispatcher | None = None,
) -> None:
    delivery = dispatcher or EmailDeliveryDispatcher()
    try:
        delivery.send(
            account,
            recipient=recipient,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            smtp_config=smtp_config,
        )
    except SmtpMailDeliveryError:
        raise
    except (EmailDeliveryError, UnsupportedProviderError) as exc:
        raise SmtpMailDeliveryError(
            str(exc.args[0]) if exc.args else "Email delivery failed",
            error_type=exc.error_code or type(exc).__name__,
        ) from exc


def deliver_smtp_account_with_dispatcher(
    account: SmtpAccount,
    *,
    recipient: str,
    subject: str,
    body: str,
    body_html: str | None = None,
    dispatcher: EmailDeliveryDispatcher | None = None,
) -> None:
    email_account, smtp_config = smtp_account_to_email_parts(account)
    deliver_with_dispatcher(
        email_account,
        recipient=recipient,
        subject=subject,
        body_text=body,
        body_html=body_html,
        smtp_config=smtp_config,
        dispatcher=dispatcher,
    )
