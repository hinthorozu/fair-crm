from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailDeliveryResult:
    success: bool
    transport: str  # "smtp" | "provider:<key>"
    external_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
