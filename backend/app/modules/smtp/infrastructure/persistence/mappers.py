"""Map between SmtpAccount aggregate and email_accounts + SMTP config tables."""

from __future__ import annotations

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.value_objects import SmtpEncryptionType


def smtp_account_to_email_parts(
    account: SmtpAccount,
) -> tuple[EmailAccount, EmailAccountSmtpConfig]:
    email_account = EmailAccount(
        id=account.id,
        organization_id=account.organization_id,
        name=account.name,
        account_type=EmailAccountType.SMTP,
        provider_key=None,
        from_email=account.from_email,
        from_name=account.from_name,
        is_default=account.is_default,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
        deleted_at=account.deleted_at,
        max_delivery_attempts=account.max_delivery_attempts,
    )
    smtp_config = EmailAccountSmtpConfig(
        email_account_id=account.id,
        host=account.host,
        port=account.port,
        username=account.username,
        password=account.password,
        encryption_type=account.encryption_type.value,
    )
    return email_account, smtp_config


def email_parts_to_smtp_account(
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
