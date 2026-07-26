"""Shared helpers around EmailDeliveryService / EmailDeliveryDispatcher."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.error_policy import ProviderErrorPolicy
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_delivery.application.dispatcher import EmailDeliveryDispatcher
from app.modules.email_delivery.domain.exceptions import (
    EmailDeliveryError,
    ProviderMessageSkippedError,
    UnsupportedProviderError,
)
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.infrastructure.persistence.mappers import smtp_account_to_email_parts


def _raise_as_smtp_error(exc: EmailDeliveryError) -> None:
    raise SmtpMailDeliveryError(
        str(exc.args[0]) if exc.args else "Email delivery failed",
        error_type=exc.error_code or type(exc).__name__,
        raw_message=str(exc.args[0]) if exc.args else None,
        retryable=exc.retryable,
        retry_after_seconds=exc.retry_after_seconds,
    ) from exc


def deliver_with_dispatcher(
    account: EmailAccount,
    *,
    recipient: str,
    subject: str,
    body_text: str | None = None,
    body_html: str | None = None,
    smtp_config: EmailAccountSmtpConfig | None = None,
    provider_config: dict[str, str] | None = None,
    error_policy: ProviderErrorPolicy | None = None,
    dispatcher: EmailDeliveryDispatcher | None = None,
) -> EmailDeliveryResult:
    """Low-level dispatch helper used by EmailDeliveryService after configs are resolved."""
    delivery = dispatcher or EmailDeliveryDispatcher()
    try:
        return delivery.send(
            account,
            recipient=recipient,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            smtp_config=smtp_config,
            provider_config=provider_config,
            error_policy=error_policy,
        )
    except SmtpMailDeliveryError:
        raise
    except ProviderMessageSkippedError as exc:
        _raise_as_smtp_error(exc)
    except (EmailDeliveryError, UnsupportedProviderError) as exc:
        _raise_as_smtp_error(exc)
    raise AssertionError("unreachable")


def deliver_smtp_account_with_dispatcher(
    account: SmtpAccount,
    *,
    recipient: str,
    subject: str,
    body: str,
    body_html: str | None = None,
    dispatcher: EmailDeliveryDispatcher | None = None,
    session: Session | None = None,
    organization_id: UUID | None = None,
) -> EmailDeliveryResult:
    """Legacy SmtpAccount entry — prefers central EmailDeliveryService when session is available."""
    if session is not None:
        from app.modules.email_delivery.application.email_delivery_service import (
            EmailDeliveryService,
        )

        return EmailDeliveryService(session, dispatcher=dispatcher).send(
            organization_id=organization_id or account.organization_id,
            email_account_id=account.id,
            to=recipient,
            subject=subject,
            body_html=body_html,
            body_text=body,
        )

    email_account, smtp_config = smtp_account_to_email_parts(account)
    if email_account.account_type == EmailAccountType.PROVIDER:
        raise SmtpMailDeliveryError(
            "Provider delivery requires a database session",
            error_type="MissingProviderSession",
            retryable=False,
        )
    return deliver_with_dispatcher(
        email_account,
        recipient=recipient,
        subject=subject,
        body_text=body,
        body_html=body_html,
        smtp_config=smtp_config,
        dispatcher=dispatcher,
    )
