"""Create a provider-type EmailAccount with generic config + error policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.email_accounts.application.provider_definitions import require_provider_definition
from app.modules.email_accounts.domain.entities import EmailAccount
from app.modules.email_accounts.domain.error_policy import ProviderErrorPolicy
from app.modules.email_accounts.domain.provider_config import EmailAccountProviderConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)

PERMISSION_CREATE = "fair_crm.email_accounts.create"


@dataclass(frozen=True)
class CreateProviderAccountCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    name: str
    provider_key: str
    provider_config: dict[str, Any]
    error_policy: dict[str, Any] | None = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    max_delivery_attempts: int = 3


class CreateProviderAccountUseCase:
    def __init__(
        self,
        repository: SqlAlchemyEmailAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateProviderAccountCommand) -> tuple[EmailAccount, EmailAccountProviderConfig]:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        definition = require_provider_definition(command.provider_key)
        existing_accounts = self._repository.list_by_organization(command.organization_id)
        should_be_default = command.is_default or len(existing_accounts) == 0
        if should_be_default:
            self._repository.clear_default_for_organization(command.organization_id)
            self._repository.flush()

        # Prefer provider config from/name; fall back to top-level fields.
        config_from_email = str(command.provider_config.get("from_email") or "").strip()
        config_from_name = str(command.provider_config.get("from_name") or "").strip()
        from_email = config_from_email or (command.from_email or "").strip()
        from_name = config_from_name or (command.from_name or None)
        if not from_email:
            raise ValueError("from_email is required")

        now = datetime.now(tz=UTC)
        account = EmailAccount.create(
            organization_id=command.organization_id,
            name=command.name,
            from_email=from_email,
            from_name=from_name,
            account_type=EmailAccountType.PROVIDER,
            provider_key=definition.provider_key,
            is_default=should_be_default,
            is_active=command.is_active,
            max_delivery_attempts=command.max_delivery_attempts,
            now=now,
        )
        provider_config = EmailAccountProviderConfig.create(
            email_account_id=account.id,
            provider_key=definition.provider_key,
            config=command.provider_config,
            error_policy=command.error_policy,
            now=now,
        )
        saved_account, saved_config = self._repository.add_provider_account(account, provider_config)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.email_account.created",
            resource_type="email_account",
            resource_id=str(saved_account.id),
            new_values={
                "name": saved_account.name,
                "from_email": saved_account.from_email,
                "account_type": saved_account.account_type.value,
                "provider_key": saved_account.provider_key,
            },
            metadata={"user_id": str(command.user_id)},
        )
        return saved_account, saved_config
