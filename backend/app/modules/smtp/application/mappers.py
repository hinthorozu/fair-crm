from app.modules.smtp.application.commands import SmtpAccountResult
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.smtp_config_validation import smtp_config_warnings


def smtp_account_to_result(account: SmtpAccount) -> SmtpAccountResult:
    return SmtpAccountResult(
        id=account.id,
        organization_id=account.organization_id,
        name=account.name,
        from_email=account.from_email,
        from_name=account.from_name,
        host=account.host,
        port=account.port,
        username=account.username,
        encryption_type=account.encryption_type,
        is_default=account.is_default,
        is_active=account.is_active,
        password_set=bool(account.password),
        created_at=account.created_at,
        updated_at=account.updated_at,
        deleted_at=account.deleted_at,
        config_warnings=tuple(smtp_config_warnings(account.port, account.encryption_type)),
    )
