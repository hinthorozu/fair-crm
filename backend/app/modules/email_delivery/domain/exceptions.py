from __future__ import annotations


class EmailDeliveryError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        transport: str | None = None,
        retryable: bool | None = None,
        retry_after_seconds: int | None = None,
        provider_status: str | None = None,
        policy_category: str | None = None,
        policy_action: str | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.transport = transport
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.provider_status = provider_status
        self.policy_category = policy_category
        self.policy_action = policy_action


class UnsupportedProviderError(EmailDeliveryError):
    """Raised when provider_key has no registered adapter."""


class ProviderMessageSkippedError(EmailDeliveryError):
    """Raised when MESSAGE_ERROR policy action is skip — non-retryable soft failure."""
