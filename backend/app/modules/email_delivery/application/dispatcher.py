from __future__ import annotations

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_delivery.application.provider_registry import (
    EmailProviderRegistry,
    create_default_provider_registry,
)
from app.modules.email_delivery.domain.exceptions import (
    EmailDeliveryError,
    UnsupportedProviderError,
)
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.email_delivery.infrastructure.smtp_sender import SmtpEmailSender


class EmailDeliveryDispatcher:
    def __init__(
        self,
        provider_registry: EmailProviderRegistry | None = None,
        smtp_sender: SmtpEmailSender | None = None,
    ):
        self._registry = provider_registry or create_default_provider_registry()
        self._smtp_sender = smtp_sender or SmtpEmailSender()

    def send(
        self,
        account: EmailAccount,
        *,
        recipient: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        smtp_config: EmailAccountSmtpConfig | None = None,
    ) -> EmailDeliveryResult:
        if account.account_type == EmailAccountType.SMTP:
            if smtp_config is None:
                raise EmailDeliveryError(
                    "SMTP config required",
                    error_code="MissingSmtpConfig",
                    transport="smtp",
                )
            return self._smtp_sender.send(
                account,
                recipient=recipient,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                smtp_config=smtp_config,
            )

        if account.account_type == EmailAccountType.PROVIDER:
            if not account.provider_key:
                raise UnsupportedProviderError(
                    "provider_key is required",
                    error_code="MissingProviderKey",
                    transport="provider",
                )
            adapter = self._registry.require(account.provider_key)
            return adapter.send(
                account,
                recipient=recipient,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
            )

        raise EmailDeliveryError(
            f"Unsupported account type: {account.account_type}",
            error_code="UnsupportedAccountType",
        )
