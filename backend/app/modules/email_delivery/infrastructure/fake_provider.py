from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.email_accounts.domain.entities import EmailAccount
from app.modules.email_delivery.domain.exceptions import EmailDeliveryError
from app.modules.email_delivery.domain.results import EmailDeliveryResult


@dataclass
class FakeProviderAdapter:
    """Test double provider adapter — records sends; can be configured to fail."""

    provider_key: str = "fake"
    fail: bool = False
    fail_error_code: str = "FakeProviderFailure"
    fail_message: str = "Fake provider configured to fail"
    external_message_id: str | None = "fake-msg-1"
    provider_status: str | None = "accepted"
    sent: list[dict[str, Any]] = field(default_factory=list)

    def send(
        self,
        account: EmailAccount,
        *,
        recipient: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        provider_config: dict[str, str] | None = None,
    ) -> EmailDeliveryResult:
        self.sent.append(
            {
                "account": account,
                "recipient": recipient,
                "subject": subject,
                "body_html": body_html,
                "body_text": body_text,
                "provider_config": provider_config or {},
            }
        )
        if self.fail:
            raise EmailDeliveryError(
                self.fail_message,
                error_code=self.fail_error_code,
                transport=f"provider:{self.provider_key}",
            )
        return EmailDeliveryResult(
            success=True,
            transport=f"provider:{self.provider_key}",
            external_message_id=self.external_message_id,
            provider_status=self.provider_status,
        )
