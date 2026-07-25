from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountSmtpConfigModel,
)
from app.shared.secret_encryption import decrypt_secret, encrypt_secret


def account_model_to_entity(model: EmailAccountModel) -> EmailAccount:
    return EmailAccount(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        account_type=EmailAccountType(model.account_type),
        provider_key=model.provider_key,
        from_email=model.from_email,
        from_name=model.from_name,
        is_default=model.is_default,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        max_delivery_attempts=model.max_delivery_attempts,
    )


def account_entity_to_model(account: EmailAccount) -> EmailAccountModel:
    return EmailAccountModel(
        id=account.id,
        organization_id=account.organization_id,
        name=account.name,
        account_type=account.account_type.value,
        provider_key=account.provider_key,
        from_email=account.from_email,
        from_name=account.from_name,
        is_default=account.is_default,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
        deleted_at=account.deleted_at,
        max_delivery_attempts=account.max_delivery_attempts,
    )


def update_account_model_from_entity(model: EmailAccountModel, account: EmailAccount) -> None:
    model.name = account.name
    model.account_type = account.account_type.value
    model.provider_key = account.provider_key
    model.from_email = account.from_email
    model.from_name = account.from_name
    model.is_default = account.is_default
    model.is_active = account.is_active
    model.max_delivery_attempts = account.max_delivery_attempts
    model.updated_at = account.updated_at
    model.deleted_at = account.deleted_at


def smtp_config_model_to_entity(model: EmailAccountSmtpConfigModel) -> EmailAccountSmtpConfig:
    return EmailAccountSmtpConfig(
        email_account_id=model.email_account_id,
        host=model.host,
        port=model.port,
        username=model.username,
        password=decrypt_secret(model.password),
        encryption_type=model.encryption_type,
    )


def smtp_config_entity_to_model(config: EmailAccountSmtpConfig) -> EmailAccountSmtpConfigModel:
    return EmailAccountSmtpConfigModel(
        email_account_id=config.email_account_id,
        host=config.host,
        port=config.port,
        username=config.username,
        password=encrypt_secret(config.password),
        encryption_type=config.encryption_type,
    )


def update_smtp_config_model_from_entity(
    model: EmailAccountSmtpConfigModel,
    config: EmailAccountSmtpConfig,
) -> None:
    model.host = config.host
    model.port = config.port
    model.username = config.username
    model.password = encrypt_secret(config.password)
    model.encryption_type = config.encryption_type
