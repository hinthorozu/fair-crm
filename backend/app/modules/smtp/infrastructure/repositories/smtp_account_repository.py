"""Repository for tenant-scoped SMTP accounts (backed by email_accounts)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.infrastructure.persistence.mappers import (
    email_parts_to_smtp_account,
    smtp_account_to_email_parts,
)


class SqlAlchemySmtpAccountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._email_accounts = SqlAlchemyEmailAccountRepository(session)

    def add(self, account: SmtpAccount) -> SmtpAccount:
        email_account, smtp_config = smtp_account_to_email_parts(account)
        saved_account, saved_config = self._email_accounts.add_smtp_account(
            email_account,
            smtp_config,
        )
        return email_parts_to_smtp_account(saved_account, saved_config)

    def update(self, account: SmtpAccount) -> SmtpAccount:
        email_account, smtp_config = smtp_account_to_email_parts(account)
        saved_account, saved_config = self._email_accounts.update_smtp_account(
            email_account,
            smtp_config,
        )
        return email_parts_to_smtp_account(saved_account, saved_config)

    def get_by_id(self, organization_id: UUID, account_id: UUID) -> SmtpAccount | None:
        pair = self._email_accounts.get_with_smtp_config(organization_id, account_id)
        if pair is None:
            return None
        account, smtp_config = pair
        if account.account_type.value != "smtp":
            return None
        return email_parts_to_smtp_account(account, smtp_config)

    def list_by_organization(self, organization_id: UUID) -> list[SmtpAccount]:
        return [
            email_parts_to_smtp_account(account, smtp_config)
            for account, smtp_config in self._email_accounts.list_smtp_by_organization(
                organization_id
            )
        ]

    def list_active_accounts(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID | None = None,
    ) -> list[SmtpAccount]:
        """Active, non-deleted SMTP accounts ordered by name, id (for default transfer)."""
        result: list[SmtpAccount] = []
        for account, smtp_config in self._email_accounts.list_smtp_by_organization(
            organization_id
        ):
            if not account.is_active:
                continue
            if exclude_account_id is not None and account.id == exclude_account_id:
                continue
            result.append(email_parts_to_smtp_account(account, smtp_config))
        return result

    def get_default_for_organization(self, organization_id: UUID) -> SmtpAccount | None:
        """Org-wide default; only returned when the default account is SMTP and active."""
        default = self._email_accounts.get_default_for_organization(organization_id)
        if default is None:
            return None
        if default.account_type.value != "smtp":
            return None
        smtp_config = self._email_accounts.get_smtp_config(default.id)
        if smtp_config is None:
            return None
        return email_parts_to_smtp_account(default, smtp_config)

    def clear_default_for_organization(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID | None = None,
    ) -> None:
        self._email_accounts.clear_default_for_organization(
            organization_id,
            exclude_account_id=exclude_account_id,
        )

    def promote_next_active_default(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID,
        now: datetime,
    ) -> None:
        """Before losing a default account: promote next active account (name, id ASC)."""
        candidates = self._email_accounts.list_active_accounts(
            organization_id,
            exclude_account_id=exclude_account_id,
        )
        if not candidates:
            return
        self._email_accounts.clear_default_for_organization(organization_id)
        self._email_accounts.flush()
        successor = candidates[0]
        successor.mark_as_default(now=now)
        self._email_accounts.update_account(successor)
        self._email_accounts.flush()

    def flush(self) -> None:
        self._email_accounts.flush()
