from __future__ import annotations

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.value_objects import SmtpEncryptionType
from app.modules.smtp.infrastructure.smtp_mailer import send_smtp_message


class SmtpEmailSender:
    """SMTP delivery path — builds SmtpAccount and reuses send_smtp_message."""

    def send(
        self,
        account: EmailAccount,
        *,
        recipient: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        smtp_config: EmailAccountSmtpConfig,
    ) -> EmailDeliveryResult:
        smtp_account = self._to_smtp_account(account, smtp_config)
        send_smtp_message(
            smtp_account,
            recipient=recipient,
            subject=subject,
            body=body_text or "",
            body_html=body_html,
        )
        return EmailDeliveryResult(
            success=True,
            transport="smtp",
            external_message_id=None,
        )

    @staticmethod
    def _to_smtp_account(
        account: EmailAccount,
        smtp_config: EmailAccountSmtpConfig,
    ) -> SmtpAccount:
        return SmtpAccount(
            id=account.id,
            organization_id=account.organization_id,
            name=account.name,
            from_email=account.from_email,
            from_name=account.from_name,
            host=smtp_config.host,
            port=smtp_config.port,
            username=smtp_config.username,
            password=smtp_config.password,
            encryption_type=SmtpEncryptionType(smtp_config.encryption_type),
            is_default=account.is_default,
            is_active=account.is_active,
            created_at=account.created_at,
            updated_at=account.updated_at,
            deleted_at=account.deleted_at,
            max_delivery_attempts=account.max_delivery_attempts,
        )
