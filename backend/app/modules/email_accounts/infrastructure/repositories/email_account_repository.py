"""Repository for tenant-scoped email account records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.persistence.mappers import (
    account_entity_to_model,
    account_model_to_entity,
    smtp_config_entity_to_model,
    smtp_config_model_to_entity,
    update_account_model_from_entity,
    update_smtp_config_model_from_entity,
)
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountSmtpConfigModel,
)


class SqlAlchemyEmailAccountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_smtp_account(
        self,
        account: EmailAccount,
        smtp_config: EmailAccountSmtpConfig,
    ) -> tuple[EmailAccount, EmailAccountSmtpConfig]:
        account_model = account_entity_to_model(account)
        config_model = smtp_config_entity_to_model(smtp_config)
        self._session.add(account_model)
        self._session.add(config_model)
        self._session.flush()
        return account_model_to_entity(account_model), smtp_config_model_to_entity(config_model)

    def update_smtp_account(
        self,
        account: EmailAccount,
        smtp_config: EmailAccountSmtpConfig,
    ) -> tuple[EmailAccount, EmailAccountSmtpConfig]:
        account_model = self._session.get(EmailAccountModel, account.id)
        if account_model is None:
            raise ValueError(f"Email account not found: {account.id}")
        config_model = self._session.get(EmailAccountSmtpConfigModel, account.id)
        if config_model is None:
            raise ValueError(f"SMTP config not found for email account: {account.id}")

        update_account_model_from_entity(account_model, account)
        update_smtp_config_model_from_entity(config_model, smtp_config)
        self._session.flush()
        return account_model_to_entity(account_model), smtp_config_model_to_entity(config_model)

    def get_by_id(self, organization_id: UUID, account_id: UUID) -> EmailAccount | None:
        stmt = select(EmailAccountModel).where(
            EmailAccountModel.organization_id == organization_id,
            EmailAccountModel.id == account_id,
            EmailAccountModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        return account_model_to_entity(model) if model is not None else None

    def get_smtp_config(self, account_id: UUID) -> EmailAccountSmtpConfig | None:
        model = self._session.get(EmailAccountSmtpConfigModel, account_id)
        return smtp_config_model_to_entity(model) if model is not None else None

    def get_with_smtp_config(
        self,
        organization_id: UUID,
        account_id: UUID,
    ) -> tuple[EmailAccount, EmailAccountSmtpConfig] | None:
        stmt = (
            select(EmailAccountModel, EmailAccountSmtpConfigModel)
            .join(
                EmailAccountSmtpConfigModel,
                EmailAccountSmtpConfigModel.email_account_id == EmailAccountModel.id,
            )
            .where(
                EmailAccountModel.organization_id == organization_id,
                EmailAccountModel.id == account_id,
                EmailAccountModel.deleted_at.is_(None),
            )
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        account_model, config_model = row
        return account_model_to_entity(account_model), smtp_config_model_to_entity(config_model)

    def list_by_organization(self, organization_id: UUID) -> list[EmailAccount]:
        stmt = (
            select(EmailAccountModel)
            .where(
                EmailAccountModel.organization_id == organization_id,
                EmailAccountModel.deleted_at.is_(None),
            )
            .order_by(EmailAccountModel.name.asc(), EmailAccountModel.id.asc())
        )
        return [account_model_to_entity(model) for model in self._session.scalars(stmt).all()]

    def list_active_accounts(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID | None = None,
    ) -> list[EmailAccount]:
        stmt = (
            select(EmailAccountModel)
            .where(
                EmailAccountModel.organization_id == organization_id,
                EmailAccountModel.deleted_at.is_(None),
                EmailAccountModel.is_active.is_(True),
            )
            .order_by(EmailAccountModel.name.asc(), EmailAccountModel.id.asc())
        )
        if exclude_account_id is not None:
            stmt = stmt.where(EmailAccountModel.id != exclude_account_id)
        return [account_model_to_entity(model) for model in self._session.scalars(stmt).all()]

    def list_smtp_by_organization(
        self,
        organization_id: UUID,
    ) -> list[tuple[EmailAccount, EmailAccountSmtpConfig]]:
        stmt = (
            select(EmailAccountModel, EmailAccountSmtpConfigModel)
            .join(
                EmailAccountSmtpConfigModel,
                EmailAccountSmtpConfigModel.email_account_id == EmailAccountModel.id,
            )
            .where(
                EmailAccountModel.organization_id == organization_id,
                EmailAccountModel.account_type == EmailAccountType.SMTP.value,
                EmailAccountModel.deleted_at.is_(None),
            )
            .order_by(EmailAccountModel.name.asc(), EmailAccountModel.id.asc())
        )
        return [
            (account_model_to_entity(account_model), smtp_config_model_to_entity(config_model))
            for account_model, config_model in self._session.execute(stmt).all()
        ]

    def get_default_for_organization(self, organization_id: UUID) -> EmailAccount | None:
        stmt = select(EmailAccountModel).where(
            EmailAccountModel.organization_id == organization_id,
            EmailAccountModel.is_default.is_(True),
            EmailAccountModel.is_active.is_(True),
            EmailAccountModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        return account_model_to_entity(model) if model is not None else None

    def clear_default_for_organization(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID | None = None,
    ) -> None:
        stmt = select(EmailAccountModel).where(
            EmailAccountModel.organization_id == organization_id,
            EmailAccountModel.is_default.is_(True),
            EmailAccountModel.deleted_at.is_(None),
        )
        if exclude_account_id is not None:
            stmt = stmt.where(EmailAccountModel.id != exclude_account_id)
        for model in self._session.scalars(stmt).all():
            model.is_default = False

    def update_account(self, account: EmailAccount) -> EmailAccount:
        model = self._session.get(EmailAccountModel, account.id)
        if model is None:
            raise ValueError(f"Email account not found: {account.id}")
        update_account_model_from_entity(model, account)
        self._session.flush()
        return account_model_to_entity(model)

    def flush(self) -> None:
        self._session.flush()
