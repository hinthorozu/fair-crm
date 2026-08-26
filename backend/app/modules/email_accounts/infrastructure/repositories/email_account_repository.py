"""Repository for tenant-scoped email account records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.provider_config import EmailAccountProviderConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.persistence.mappers import (
    account_entity_to_model,
    account_model_to_entity,
    provider_config_entity_to_model,
    provider_config_model_to_entity,
    smtp_config_entity_to_model,
    smtp_config_model_to_entity,
    update_account_model_from_entity,
    update_provider_config_model_from_entity,
    update_smtp_config_model_from_entity,
)
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
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
        account_model = self._session.scalars(
            select(EmailAccountModel).where(
                EmailAccountModel.organization_id == account.organization_id,
                EmailAccountModel.id == account.id,
                EmailAccountModel.deleted_at.is_(None),
            )
        ).one_or_none()
        if account_model is None:
            raise ValueError(f"Email account not found: {account.id}")
        config_model = self._session.get(EmailAccountSmtpConfigModel, account.id)
        if config_model is None:
            raise ValueError(f"SMTP config not found for email account: {account.id}")

        update_account_model_from_entity(account_model, account)
        update_smtp_config_model_from_entity(config_model, smtp_config)
        self._session.flush()
        return account_model_to_entity(account_model), smtp_config_model_to_entity(config_model)

    def add_provider_account(
        self,
        account: EmailAccount,
        provider_config: EmailAccountProviderConfig,
    ) -> tuple[EmailAccount, EmailAccountProviderConfig]:
        account_model = account_entity_to_model(account)
        config_model = provider_config_entity_to_model(provider_config)
        self._session.add(account_model)
        self._session.add(config_model)
        self._session.flush()
        return account_model_to_entity(account_model), provider_config_model_to_entity(config_model)

    def update_provider_account(
        self,
        account: EmailAccount,
        provider_config: EmailAccountProviderConfig,
    ) -> tuple[EmailAccount, EmailAccountProviderConfig]:
        account_model = self._session.scalars(
            select(EmailAccountModel).where(
                EmailAccountModel.organization_id == account.organization_id,
                EmailAccountModel.id == account.id,
                EmailAccountModel.deleted_at.is_(None),
            )
        ).one_or_none()
        if account_model is None:
            raise ValueError(f"Email account not found: {account.id}")
        config_model = self._session.get(EmailAccountProviderConfigModel, account.id)
        if config_model is None:
            raise ValueError(f"Provider config not found for email account: {account.id}")

        update_account_model_from_entity(account_model, account)
        update_provider_config_model_from_entity(config_model, provider_config)
        self._session.flush()
        return account_model_to_entity(account_model), provider_config_model_to_entity(config_model)

    def get_provider_config(
        self,
        account_id: UUID,
        *,
        organization_id: UUID | None = None,
    ) -> EmailAccountProviderConfig | None:
        if organization_id is None:
            model = self._session.get(EmailAccountProviderConfigModel, account_id)
            return provider_config_model_to_entity(model) if model is not None else None
        stmt = (
            select(EmailAccountProviderConfigModel)
            .join(
                EmailAccountModel,
                EmailAccountModel.id == EmailAccountProviderConfigModel.email_account_id,
            )
            .where(
                EmailAccountModel.organization_id == organization_id,
                EmailAccountModel.id == account_id,
                EmailAccountModel.deleted_at.is_(None),
            )
        )
        model = self._session.scalars(stmt).one_or_none()
        return provider_config_model_to_entity(model) if model is not None else None

    def get_with_provider_config(
        self,
        organization_id: UUID,
        account_id: UUID,
    ) -> tuple[EmailAccount, EmailAccountProviderConfig] | None:
        stmt = (
            select(EmailAccountModel, EmailAccountProviderConfigModel)
            .join(
                EmailAccountProviderConfigModel,
                EmailAccountProviderConfigModel.email_account_id == EmailAccountModel.id,
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
        return account_model_to_entity(account_model), provider_config_model_to_entity(config_model)

    def get_by_id(self, organization_id: UUID, account_id: UUID) -> EmailAccount | None:
        stmt = select(EmailAccountModel).where(
            EmailAccountModel.organization_id == organization_id,
            EmailAccountModel.id == account_id,
            EmailAccountModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        return account_model_to_entity(model) if model is not None else None

    def get_by_id_unscoped(self, account_id: UUID) -> EmailAccount | None:
        """Load account by id without organization filter (webhook ingress).

        Does not require ``is_active`` — inactive accounts may still receive
        delayed provider webhooks for previously sent messages.
        """
        stmt = select(EmailAccountModel).where(
            EmailAccountModel.id == account_id,
            EmailAccountModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        return account_model_to_entity(model) if model is not None else None

    def get_smtp_config(
        self,
        account_id: UUID,
        *,
        organization_id: UUID | None = None,
    ) -> EmailAccountSmtpConfig | None:
        if organization_id is None:
            model = self._session.get(EmailAccountSmtpConfigModel, account_id)
            return smtp_config_model_to_entity(model) if model is not None else None
        stmt = (
            select(EmailAccountSmtpConfigModel)
            .join(
                EmailAccountModel,
                EmailAccountModel.id == EmailAccountSmtpConfigModel.email_account_id,
            )
            .where(
                EmailAccountModel.organization_id == organization_id,
                EmailAccountModel.id == account_id,
                EmailAccountModel.deleted_at.is_(None),
            )
        )
        model = self._session.scalars(stmt).one_or_none()
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
        model = self._session.scalars(
            select(EmailAccountModel).where(
                EmailAccountModel.organization_id == account.organization_id,
                EmailAccountModel.id == account.id,
                EmailAccountModel.deleted_at.is_(None),
            )
        ).one_or_none()
        if model is None:
            raise ValueError(f"Email account not found: {account.id}")
        update_account_model_from_entity(model, account)
        self._session.flush()
        return account_model_to_entity(model)

    def promote_next_active_default(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID,
        now,
    ) -> EmailAccount | None:
        candidates = self.list_active_accounts(
            organization_id,
            exclude_account_id=exclude_account_id,
        )
        if not candidates:
            return None
        self.clear_default_for_organization(organization_id)
        self.flush()
        successor = candidates[0]
        successor.mark_as_default(now=now)
        return self.update_account(successor)

    def flush(self) -> None:
        self._session.flush()
