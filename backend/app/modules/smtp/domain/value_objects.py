from enum import StrEnum


class SmtpEncryptionType(StrEnum):
    NONE = "none"
    SSL = "ssl"
    TLS = "tls"
    STARTTLS = "starttls"
