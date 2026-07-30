"""Email account provider config aggregate (generic credentials + error policy)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.modules.email_accounts.application.provider_definitions import (
    ProviderDefinition,
    require_provider_definition,
)
from app.modules.email_accounts.domain.error_policy import (
    ProviderErrorPolicy,
    ProviderErrorPolicyValidationError,
)
from app.shared.email import sanitize_scraped_email


@dataclass
class EmailAccountProviderConfig:
    email_account_id: UUID
    provider_key: str
    config: dict[str, str]
    error_policy: ProviderErrorPolicy
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        email_account_id: UUID,
        provider_key: str,
        config: dict[str, Any],
        error_policy: ProviderErrorPolicy | dict[str, Any] | None,
        now: datetime,
    ) -> EmailAccountProviderConfig:
        definition = require_provider_definition(provider_key)
        normalized_config = normalize_provider_config(definition, config, existing=None)
        policy = (
            error_policy
            if isinstance(error_policy, ProviderErrorPolicy)
            else ProviderErrorPolicy.from_dict(error_policy)
        )
        return cls(
            email_account_id=email_account_id,
            provider_key=definition.provider_key,
            config=normalized_config,
            error_policy=policy,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        config: dict[str, Any] | None = None,
        error_policy: ProviderErrorPolicy | dict[str, Any] | None = None,
        now: datetime,
    ) -> None:
        definition = require_provider_definition(self.provider_key)
        if config is not None:
            self.config = normalize_provider_config(definition, config, existing=self.config)
        if error_policy is not None:
            self.error_policy = (
                error_policy
                if isinstance(error_policy, ProviderErrorPolicy)
                else ProviderErrorPolicy.from_dict(error_policy)
            )
        self.updated_at = now


def normalize_provider_config(
    definition: ProviderDefinition,
    incoming: dict[str, Any],
    *,
    existing: dict[str, str] | None,
) -> dict[str, str]:
    """Validate provider field values; preserve secrets when blank on update."""
    if not isinstance(incoming, dict):
        raise ValueError("provider_config must be an object")

    result: dict[str, str] = dict(existing or {})
    secret_keys = definition.secret_field_keys()
    is_create = existing is None

    for field_def in definition.fields:
        raw = incoming.get(field_def.key)
        value = "" if raw is None else str(raw).strip()

        if field_def.key in secret_keys:
            if value:
                result[field_def.key] = value
            elif is_create and field_def.required:
                raise ValueError(f"{field_def.key} is required")
            # edit + blank → keep existing
            continue

        if not value:
            if field_def.required:
                raise ValueError(f"{field_def.key} is required")
            result[field_def.key] = ""
            continue

        if field_def.field_type == "email":
            cleaned = sanitize_scraped_email(value)
            if cleaned is None:
                raise ValueError(f"{field_def.key} must be a valid email address")
            result[field_def.key] = cleaned
            continue
        result[field_def.key] = value

    for field_def in definition.fields:
        if field_def.required and not (result.get(field_def.key) or "").strip():
            raise ValueError(f"{field_def.key} is required")

    return result


def mask_provider_config(
    definition: ProviderDefinition,
    config: dict[str, str],
) -> tuple[dict[str, str | None], dict[str, bool]]:
    """Return API-safe config (secrets nulled) and secrets_set flags."""
    masked: dict[str, str | None] = {}
    secrets_set: dict[str, bool] = {}
    secret_keys = definition.secret_field_keys()
    for field_def in definition.fields:
        value = config.get(field_def.key)
        if field_def.key in secret_keys:
            secrets_set[field_def.key] = bool(value)
            masked[field_def.key] = None
        else:
            masked[field_def.key] = value
    return masked, secrets_set
