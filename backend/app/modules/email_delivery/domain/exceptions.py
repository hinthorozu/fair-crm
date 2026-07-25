from __future__ import annotations


class EmailDeliveryError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        transport: str | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.transport = transport


class UnsupportedProviderError(EmailDeliveryError):
    """Raised when provider_key has no registered adapter."""
