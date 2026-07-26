"""Map email account aggregates to API response dicts (secrets masked)."""

from __future__ import annotations

from typing import Any

from app.modules.email_accounts.application.provider_definitions import get_provider_definition
from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.provider_config import (
    EmailAccountProviderConfig,
    mask_provider_config,
)
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.smtp.domain.smtp_config_validation import smtp_config_warnings


def email_account_to_response_dict(
    account: EmailAccount,
    *,
    smtp_config: EmailAccountSmtpConfig | None = None,
    provider_config: EmailAccountProviderConfig | None = None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": account.id,
        "organization_id": account.organization_id,
        "name": account.name,
        "account_type": account.account_type.value,
        "provider_key": account.provider_key,
        "from_email": account.from_email,
        "from_name": account.from_name,
        "is_default": account.is_default,
        "is_active": account.is_active,
        "max_delivery_attempts": account.max_delivery_attempts,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
        "deleted_at": account.deleted_at,
        "config_warnings": [],
        "host": None,
        "port": None,
        "username": None,
        "encryption_type": None,
        "password_set": False,
        "provider_config": None,
        "secrets_set": {},
        "error_policy": None,
    }

    if account.account_type == EmailAccountType.SMTP and smtp_config is not None:
        base.update(
            {
                "host": smtp_config.host,
                "port": smtp_config.port,
                "username": smtp_config.username,
                "encryption_type": smtp_config.encryption_type,
                "password_set": bool(smtp_config.password),
                "config_warnings": list(
                    smtp_config_warnings(smtp_config.port, smtp_config.encryption_type)
                ),
            }
        )
    elif account.account_type == EmailAccountType.PROVIDER and provider_config is not None:
        definition = get_provider_definition(provider_config.provider_key)
        if definition is not None:
            masked, secrets_set = mask_provider_config(definition, provider_config.config)
        else:
            masked, secrets_set = dict(provider_config.config), {}
            for key in list(masked.keys()):
                if key in {"api_token", "api_key", "password", "secret"}:
                    secrets_set[key] = bool(masked.get(key))
                    masked[key] = None
        base.update(
            {
                "provider_config": masked,
                "secrets_set": secrets_set,
                "error_policy": provider_config.error_policy.to_dict(),
                "password_set": bool(secrets_set.get("api_token")),
            }
        )
    return base
