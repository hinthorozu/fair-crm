"""Update a provider-type EmailAccount config + common fields."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.email_accounts.domain.entities import EmailAccount
from app.modules.email_accounts.domain.exceptions import (
    EmailAccountAlreadyDeletedError,
    EmailAccountNotFoundError,
)
from app.modules.email_accounts.domain.provider_config import EmailAccountProviderConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)

PERMISSION_UPDATE = "fair_crm.email_accounts.update"


@dataclass(frozen=True)
class UpdateProviderAccountCommand:
    organization_id: UUID
    account_id: UUID
    access_token: str
    user_id: UUID
    name: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    max_delivery_attempts: Optional[int] = None
    provider_config: dict[str, Any] | None = None
    error_policy: dict[str, Any] | None = None


class UpdateProviderAccountUseCase:
    def __init__(
        self,
        repository: SqlAlchemyEmailAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateProviderAccountCommand) -> tuple[EmailAccount, EmailAccountProviderConfig]:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        pair = self._repository.get_with_provider_config(
            command.organization_id, command.account_id
        )
        if pair is None:
            raise EmailAccountNotFoundError("Email account not found")
        account, provider_config = pair
        if account.account_type != EmailAccountType.PROVIDER:
            raise ValueError("Account is not a provider account")
        if account.deleted_at is not None:
            raise EmailAccountAlreadyDeletedError("Email account is deleted")

        now = datetime.now(tz=UTC)
        becoming_default = command.is_default is True and not account.is_default
        becoming_inactive_default = (
            command.is_active is False and account.is_active and account.is_default
        )

        if becoming_default:
            self._repository.clear_default_for_organization(
                command.organization_id, exclude_account_id=account.id
            )
            self._repository.flush()

        if becoming_inactive_default:
            self._repository.promote_next_active_default(
                command.organization_id,
                exclude_account_id=account.id,
                now=now,
            )

        # Sync from_email/from_name from provider_config when provided.
        from_email = command.from_email
        from_name = command.from_name
        if command.provider_config is not None:
            cfg_email = str(command.provider_config.get("from_email") or "").strip()
            cfg_name = command.provider_config.get("from_name")
            if cfg_email:
                from_email = cfg_email
            if cfg_name is not None:
                from_name = str(cfg_name).strip() or None

        account.update_common_fields(
            name=command.name,
            from_email=from_email,
            from_name=from_name,
            is_default=False if becoming_inactive_default else command.is_default,
            is_active=command.is_active,
            max_delivery_attempts=command.max_delivery_attempts,
            now=now,
        )
        if command.provider_config is not None or command.error_policy is not None:
            provider_config.update(
                config=command.provider_config,
                error_policy=command.error_policy,
                now=now,
            )

        saved_account, saved_config = self._repository.update_provider_account(
            account, provider_config
        )

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.email_account.updated",
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
