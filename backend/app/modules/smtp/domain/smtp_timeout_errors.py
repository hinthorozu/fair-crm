"""SMTP timeout detection and normalized error codes."""

from __future__ import annotations

import smtplib
import socket
from typing import Literal

SmtpDeliveryPhase = Literal["connect", "send"]

SMTP_CONNECT_TIMEOUT_CODE = "smtp_connect_timeout"
SMTP_TIMEOUT_CODE = "smtp_timeout"

CONNECT_TIMEOUT_USER_MESSAGE = (
    "SMTP bağlantısı zaman aşımına uğradı. Host erişilebilirliğini ve port/firewall ayarlarını kontrol edin."
)
SEND_TIMEOUT_USER_MESSAGE = (
    "SMTP gönderimi zaman aşımına uğradı. Sunucu yanıt süresini ve ağ bağlantısını kontrol edin."
)
OPERATION_TIMEOUT_USER_MESSAGE = (
    "Mail gönderimi zaman aşımına uğradı. SMTP sunucusu yanıt vermedi."
)


def is_timeout_related_exception(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, smtplib.SMTPConnectError):
        return True
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        message = str(exc).lower()
        return "timed out" in message or "timeout" in message
    return False


def build_timeout_user_message(
    *,
    phase: SmtpDeliveryPhase,
    connect_timeout_seconds: int,
    send_timeout_seconds: int,
    operation_timeout_seconds: int | None = None,
) -> str:
    if operation_timeout_seconds is not None:
        return (
            f"{OPERATION_TIMEOUT_USER_MESSAGE} "
            f"(maksimum süre: {operation_timeout_seconds} saniye)"
        )
    if phase == "connect":
        return f"{CONNECT_TIMEOUT_USER_MESSAGE} (bağlantı süresi: {connect_timeout_seconds} saniye)"
    return f"{SEND_TIMEOUT_USER_MESSAGE} (gönderim süresi: {send_timeout_seconds} saniye)"


def normalize_timeout_error_code(*, phase: SmtpDeliveryPhase) -> str:
    if phase == "connect":
        return SMTP_CONNECT_TIMEOUT_CODE
    return SMTP_TIMEOUT_CODE


def timeout_log_message(error_code: str) -> str:
    if error_code == SMTP_CONNECT_TIMEOUT_CODE:
        return "SMTP bağlantısı zaman aşımına uğradı"
    return "SMTP gönderimi zaman aşımına uğradı"
