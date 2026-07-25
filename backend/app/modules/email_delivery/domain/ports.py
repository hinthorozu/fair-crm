from __future__ import annotations

from typing import Protocol

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_delivery.domain.results import EmailDeliveryResult


class EmailDeliveryPort(Protocol):
    def send(
        self,
        account: EmailAccount,
        *,
        recipient: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        smtp_config: EmailAccountSmtpConfig | None = None,
    ) -> EmailDeliveryResult: ...


class EmailProviderAdapter(Protocol):
    provider_key: str

    def send(
        self,
        account: EmailAccount,
        *,
        recipient: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
    ) -> EmailDeliveryResult: ...
