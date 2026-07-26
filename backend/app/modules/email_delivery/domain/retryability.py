"""Classify delivery error codes as retryable vs permanent failures."""

from __future__ import annotations

_RETRYABLE_ERROR_CODES = frozenset(
    {
        "TimeoutError",
        "timeout",  # socket.timeout
        "SMTPConnectError",
        "SMTPServerDisconnected",
        "ConnectionRefusedError",
        "ConnectionError",
        "OSError",
        "gaierror",
        "SMTPException",  # generic temporary-looking SMTP failures
        "SSLError",  # generic TLS handshake flakes; wrong-version handled below
    }
)

_NON_RETRYABLE_ERROR_CODES = frozenset(
    {
        "SMTPAuthenticationError",
        "SMTPRecipientsRefused",
        "SMTPSenderRefused",
        "InactiveAccount",
        "SmtpAccountNotFound",
        "SmtpAccountAlreadyDeleted",
        "EmailAccountNotFound",
        "EmailAccountAlreadyDeleted",
        "UnsupportedProviderError",
        "InvalidSmtpTestRecipientError",
        "consent_blocked",
    }
)

# Substrings that indicate permanent SSL/TLS configuration mistakes.
_PERMANENT_SSL_MESSAGE_MARKERS = (
    "wrong version number",
    "ssl wrong version",
    "unsupported protocol",
    "certificate verify failed",
)


def is_retryable_delivery_error(
    error_code: str | None,
    *,
    error_message: str | None = None,
) -> bool:
    """Return True when the worker may auto-requeue the mail send operation."""
    if not error_code:
        return False

    code = error_code.strip()
    if not code:
        return False

    if code in _NON_RETRYABLE_ERROR_CODES:
        return False

    message = (error_message or "").lower()
    if code in {"SSLError", "OSError"} and any(
        marker in message for marker in _PERMANENT_SSL_MESSAGE_MARKERS
    ):
        return False

    if code in _RETRYABLE_ERROR_CODES:
        return True

    # Temporary-looking SMTP reply codes (4xx) sometimes appear in messages.
    if "4. " in message or "try again" in message or "temporarily" in message:
        return True

    return False
