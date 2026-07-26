from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailDeliveryResult:
    success: bool
    transport: str  # "smtp" | "provider:<key>"
    external_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    provider_status: str | None = None
    raw_error_code: str | None = None
    raw_error_message: str | None = None
    retryable: bool | None = None
    retry_after_seconds: int | None = None
    policy_category: str | None = None
    policy_action: str | None = None
