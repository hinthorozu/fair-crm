import logging
from uuid import UUID

from app.modules.mail_templates.domain.entities import MailTemplate
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError

logger = logging.getLogger(__name__)

SMTP_PASSWORD_USER_MESSAGE = (
    "SMTP şifresi yapılandırılmamış veya çözümlenemiyor. Lütfen SMTP hesabını yeniden kaydedin."
)


def log_mail_template_test_email_failure(
    *,
    template: MailTemplate,
    organization_id: UUID,
    smtp_account: SmtpAccount | None,
    to_email: str,
    reason: str | None = None,
    exc: SmtpMailDeliveryError | None = None,
) -> None:
    payload = {
        "event": "mail_template_test_email_failed",
        "template_id": str(template.id),
        "template_key": template.key,
        "template_name": template.name,
        "organization_id": str(organization_id),
        "to_email": to_email,
        "reason": reason,
    }
    if smtp_account is not None:
        payload.update(
            {
                "smtp_account_id": str(smtp_account.id),
                "smtp_host": smtp_account.host,
                "smtp_port": smtp_account.port,
                "encryption_type": smtp_account.encryption_type.value,
            }
        )
    if exc is not None:
        payload["exception_type"] = exc.error_type or type(exc).__name__
        payload["message"] = exc.args[0] if exc.args else str(exc)
    logger.warning(
        "mail_template_test_email_failed %s",
        " ".join(f"{key}={value}" for key, value in payload.items() if value is not None),
    )
