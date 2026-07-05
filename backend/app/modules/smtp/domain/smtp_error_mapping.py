"""Map SMTP delivery exceptions to safe user-facing messages."""

from __future__ import annotations

import smtplib
import socket
import ssl
from socket import gaierror

from app.modules.smtp.domain.smtp_config_validation import (
    GENERIC_CONNECTION_USER_MESSAGE,
    SSL_WRONG_VERSION_USER_MESSAGE,
    is_ssl_wrong_version_error,
)

AUTHENTICATION_USER_MESSAGE = (
    "SMTP kimlik doğrulaması başarısız. Kullanıcı adı veya şifreyi kontrol edin."
)
CONNECT_USER_MESSAGE = (
    "SMTP sunucusuna bağlanılamadı. Host ve port ayarlarını kontrol edin."
)
DISCONNECTED_USER_MESSAGE = (
    "SMTP sunucusu bağlantıyı kapattı. Ayarları ve sağlayıcı limitlerini kontrol edin."
)
RECIPIENTS_REFUSED_USER_MESSAGE = (
    "Test alıcı adresi SMTP sunucusu tarafından reddedildi. Alıcı adresini kontrol edin."
)
SENDER_REFUSED_USER_MESSAGE = (
    "Gönderen adresi SMTP sunucusu tarafından reddedildi. From email ayarını kontrol edin."
)
TIMEOUT_USER_MESSAGE = (
    "SMTP bağlantısı zaman aşımına uğradı. Host erişilebilirliğini ve port/firewall ayarlarını kontrol edin."
)
CONNECTION_REFUSED_USER_MESSAGE = (
    "SMTP sunucusu bağlantıyı reddetti. Host, port ve firewall ayarlarını kontrol edin."
)
DNS_USER_MESSAGE = "SMTP sunucu adı çözümlenemedi. Host adresini kontrol edin."
DELIVERY_USER_MESSAGE = "SMTP gönderimi başarısız oldu. Sunucu yanıtını ve ayarları kontrol edin."


def map_smtp_exception(exc: BaseException) -> tuple[str, str, str]:
    """Return (user_message, error_type, raw_message)."""
    error_type = type(exc).__name__
    raw_message = str(exc)

    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return AUTHENTICATION_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, smtplib.SMTPConnectError):
        return CONNECT_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return DISCONNECTED_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return RECIPIENTS_REFUSED_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return SENDER_REFUSED_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return TIMEOUT_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, ssl.SSLError):
        if is_ssl_wrong_version_error(exc):
            return SSL_WRONG_VERSION_USER_MESSAGE, error_type, raw_message
        return GENERIC_CONNECTION_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, ConnectionRefusedError):
        return CONNECTION_REFUSED_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, gaierror):
        return DNS_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, smtplib.SMTPException):
        return DELIVERY_USER_MESSAGE, error_type, raw_message
    if isinstance(exc, OSError):
        if is_ssl_wrong_version_error(exc):
            return SSL_WRONG_VERSION_USER_MESSAGE, error_type, raw_message
        return GENERIC_CONNECTION_USER_MESSAGE, error_type, raw_message

    return DELIVERY_USER_MESSAGE, error_type, raw_message
