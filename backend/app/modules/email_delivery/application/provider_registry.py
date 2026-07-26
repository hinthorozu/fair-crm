from __future__ import annotations

from app.modules.email_delivery.domain.exceptions import UnsupportedProviderError
from app.modules.email_delivery.domain.ports import EmailProviderAdapter
from app.modules.email_delivery.infrastructure.mailersend_adapter import MailerSendAdapter


class EmailProviderRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, EmailProviderAdapter] = {}

    def register(self, adapter: EmailProviderAdapter) -> None:
        self._adapters[adapter.provider_key] = adapter

    def get(self, provider_key: str) -> EmailProviderAdapter | None:
        return self._adapters.get(provider_key)

    def require(self, provider_key: str) -> EmailProviderAdapter:
        adapter = self.get(provider_key)
        if adapter is None:
            raise UnsupportedProviderError(
                f"No adapter registered for provider_key={provider_key!r}",
                error_code="UnsupportedProvider",
                transport=f"provider:{provider_key}",
                retryable=False,
            )
        return adapter

    def registered_keys(self) -> list[str]:
        return sorted(self._adapters.keys())


def create_default_provider_registry() -> EmailProviderRegistry:
    registry = EmailProviderRegistry()
    registry.register(MailerSendAdapter())
    return registry
