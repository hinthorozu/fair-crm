"""Turkish display labels for mail send operation list responses."""

from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)

SOURCE_TYPE_LABELS: dict[str, str] = {
    MailSendSourceType.SMTP_TEST: "SMTP Test",
    MailSendSourceType.TEMPLATE_TEST: "Şablon Test",
    MailSendSourceType.WELCOME_EMAIL: "Hoş Geldin",
    MailSendSourceType.PASSWORD_RESET: "Şifre Sıfırlama",
    MailSendSourceType.FAIR_BULK_EMAIL: "Fuar Toplu Mail",
    MailSendSourceType.MANUAL_EMAIL: "Manuel E-posta",
    MailSendSourceType.SYSTEM_NOTIFICATION: "Sistem Bildirimi",
}

STATUS_LABELS: dict[str, str] = {
    MailSendOperationStatus.QUEUED: "Kuyrukta",
    MailSendOperationStatus.SENDING: "Gönderiliyor",
    MailSendOperationStatus.SENT: "Gönderildi",
    MailSendOperationStatus.FAILED: "Başarısız",
    MailSendOperationStatus.CANCELLED: "İptal Edildi",
}


def source_type_label(source_type: str) -> str:
    return SOURCE_TYPE_LABELS.get(source_type, source_type)


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)
