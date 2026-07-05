"""Soft (non-blocking) SMTP port / encryption compatibility warnings."""

from __future__ import annotations

from app.modules.smtp.domain.value_objects import SmtpEncryptionType

SSL_PORT = 465
STARTTLS_PORT = 587

SSL_PORT_WARNING = (
    "SSL genelde 465 portu ile kullanılır. Mevcut port ayarı beklenen değerden farklı olabilir."
)
STARTTLS_PORT_WARNING = (
    "STARTTLS genelde 587 portu ile kullanılır. Mevcut port ayarı beklenen değerden farklı olabilir."
)
NONE_ON_465_WARNING = (
    "Şifreleme kapalıyken 465 portu genelde SSL/TLS gerektirir; ssl veya tls seçmeyi deneyin."
)
TLS_PORT_WARNING = (
    "TLS ayarları sağlayıcıya göre değişebilir; 465 dışı bir port seçtiyseniz kombinasyonu doğrulayın."
)

SSL_WRONG_VERSION_USER_MESSAGE = (
    "SMTP SSL bağlantı hatası: Şifreleme türü ile port uyumsuz olabilir. "
    "SSL için 465, STARTTLS için 587 deneyin."
)

GENERIC_CONNECTION_USER_MESSAGE = (
    "SMTP sunucusuna bağlanılamadı. Host, port ve şifreleme ayarlarını kontrol edin."
)


def smtp_config_warnings(port: int, encryption_type: SmtpEncryptionType | str) -> list[str]:
    if isinstance(encryption_type, str):
        encryption_type = SmtpEncryptionType(encryption_type)

    warnings: list[str] = []

    if encryption_type == SmtpEncryptionType.SSL and port != SSL_PORT:
        warnings.append(SSL_PORT_WARNING)
    elif encryption_type == SmtpEncryptionType.STARTTLS and port != STARTTLS_PORT:
        warnings.append(STARTTLS_PORT_WARNING)
    elif encryption_type == SmtpEncryptionType.NONE and port == SSL_PORT:
        warnings.append(NONE_ON_465_WARNING)
    elif encryption_type == SmtpEncryptionType.TLS and port != SSL_PORT:
        warnings.append(TLS_PORT_WARNING)

    return warnings


def is_ssl_wrong_version_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "wrong_version_number" in text


def user_facing_connection_error(exc: BaseException) -> str:
    from app.modules.smtp.domain.smtp_error_mapping import map_smtp_exception

    user_message, _, _ = map_smtp_exception(exc)
    return user_message
