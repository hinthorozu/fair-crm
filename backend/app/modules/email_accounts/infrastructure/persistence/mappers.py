import json
from typing import Any

from app.modules.email_accounts.application.provider_definitions import get_provider_definition
from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.error_policy import ProviderErrorPolicy
from app.modules.email_accounts.domain.provider_config import EmailAccountProviderConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
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


def _encrypt_config_values(provider_key: str, config: dict[str, str]) -> dict[str, str]:
    definition = get_provider_definition(provider_key)
    secret_keys = definition.secret_field_keys() if definition else frozenset()
    stored: dict[str, str] = {}
    for key, value in config.items():
        if key in secret_keys:
            stored[key] = encrypt_secret(value) or ""
        else:
            stored[key] = value
    return stored


def _decrypt_config_values(provider_key: str, stored: dict[str, Any]) -> dict[str, str]:
    definition = get_provider_definition(provider_key)
    secret_keys = definition.secret_field_keys() if definition else frozenset()
    result: dict[str, str] = {}
    for key, value in stored.items():
        text = "" if value is None else str(value)
        if key in secret_keys:
            result[key] = decrypt_secret(text) or ""
        else:
            result[key] = text
    return result


def provider_config_model_to_entity(
    model: EmailAccountProviderConfigModel,
) -> EmailAccountProviderConfig:
    raw_config = json.loads(model.config_json or "{}")
    if not isinstance(raw_config, dict):
        raw_config = {}
    raw_policy = json.loads(model.error_policy_json or "{}")
    if not isinstance(raw_policy, dict):
        raw_policy = {}
    return EmailAccountProviderConfig(
        email_account_id=model.email_account_id,
        provider_key=model.provider_key,
        config=_decrypt_config_values(model.provider_key, raw_config),
        error_policy=ProviderErrorPolicy.from_dict(raw_policy),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def provider_config_entity_to_model(
    config: EmailAccountProviderConfig,
) -> EmailAccountProviderConfigModel:
    return EmailAccountProviderConfigModel(
        email_account_id=config.email_account_id,
        provider_key=config.provider_key,
        config_json=json.dumps(_encrypt_config_values(config.provider_key, config.config)),
        error_policy_json=json.dumps(config.error_policy.to_dict()),
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def update_provider_config_model_from_entity(
    model: EmailAccountProviderConfigModel,
    config: EmailAccountProviderConfig,
) -> None:
    model.provider_key = config.provider_key
    model.config_json = json.dumps(_encrypt_config_values(config.provider_key, config.config))
    model.error_policy_json = json.dumps(config.error_policy.to_dict())
    model.updated_at = config.updated_at
