"""Classify delivery error codes for worker auto-retry."""

from app.modules.email_delivery.domain.retryability import is_retryable_delivery_error


def test_retryable_timeout_and_connection_codes():
    for code in (
        "TimeoutError",
        "timeout",
        "SMTPConnectError",
        "SMTPServerDisconnected",
        "ConnectionRefusedError",
        "ConnectionError",
        "OSError",
    ):
        assert is_retryable_delivery_error(code) is True


def test_non_retryable_auth_and_account_codes():
    for code in (
        "SMTPAuthenticationError",
        "SMTPRecipientsRefused",
        "SMTPSenderRefused",
        "InactiveAccount",
        "SmtpAccountNotFound",
        "SmtpAccountAlreadyDeleted",
    ):
        assert is_retryable_delivery_error(code) is False


def test_ssl_wrong_version_is_permanent():
    assert (
        is_retryable_delivery_error(
            "SSLError",
            error_message="[SSL: WRONG_VERSION_NUMBER] wrong version number",
        )
        is False
    )


def test_generic_ssl_error_without_permanent_marker_is_retryable():
    assert is_retryable_delivery_error("SSLError", error_message="handshake failed") is True


def test_none_or_empty_not_retryable():
    assert is_retryable_delivery_error(None) is False
    assert is_retryable_delivery_error("") is False
    assert is_retryable_delivery_error("   ") is False
