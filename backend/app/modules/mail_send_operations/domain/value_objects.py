from enum import StrEnum


class MailSendSourceType(StrEnum):
    SMTP_TEST = "smtp_test"
    TEMPLATE_TEST = "template_test"
    WELCOME_EMAIL = "welcome_email"
    PASSWORD_RESET = "password_reset"
    FAIR_BULK_EMAIL = "fair_bulk_email"
    MANUAL_EMAIL = "manual_email"
    MANUAL_TASK_MAIL = "manual_task_mail"
    SYSTEM_NOTIFICATION = "system_notification"


class MailSendOperationStatus(StrEnum):
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


MAIL_SEND_SOURCE_PRIORITY: dict[MailSendSourceType, int] = {
    MailSendSourceType.PASSWORD_RESET: 10,
    MailSendSourceType.WELCOME_EMAIL: 20,
    MailSendSourceType.SMTP_TEST: 40,
    MailSendSourceType.TEMPLATE_TEST: 40,
    MailSendSourceType.MANUAL_EMAIL: 50,
    MailSendSourceType.MANUAL_TASK_MAIL: 50,
    MailSendSourceType.SYSTEM_NOTIFICATION: 60,
    MailSendSourceType.FAIR_BULK_EMAIL: 99,
}


def priority_for_source(source_type: MailSendSourceType | str) -> int:
    try:
        normalized = MailSendSourceType(source_type)
    except ValueError as exc:
        raise ValueError(f"Unknown mail send source type: {source_type}") from exc
    return MAIL_SEND_SOURCE_PRIORITY[normalized]
