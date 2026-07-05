"""Repository for tenant-scoped SMTP account records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.smtp.infrastructure.persistence.models import SmtpAccountModel


class SqlAlchemySmtpAccountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, account: SmtpAccount) -> SmtpAccount:
        model = entity_to_model(account)
        self._session.add(model)
        self._session.flush()
        return model_to_entity(model)

    def update(self, account: SmtpAccount) -> SmtpAccount:
        model = self._session.get(SmtpAccountModel, account.id)
        if model is None:
            raise ValueError(f"SMTP account not found: {account.id}")
        update_model_from_entity(model, account)
        self._session.flush()
        return model_to_entity(model)

    def get_by_id(self, organization_id: UUID, account_id: UUID) -> SmtpAccount | None:
        stmt = select(SmtpAccountModel).where(
            SmtpAccountModel.organization_id == organization_id,
            SmtpAccountModel.id == account_id,
            SmtpAccountModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        return model_to_entity(model) if model is not None else None

    def list_by_organization(self, organization_id: UUID) -> list[SmtpAccount]:
        stmt = (
            select(SmtpAccountModel)
            .where(
                SmtpAccountModel.organization_id == organization_id,
                SmtpAccountModel.deleted_at.is_(None),
            )
            .order_by(SmtpAccountModel.name.asc(), SmtpAccountModel.id.asc())
        )
        return [model_to_entity(model) for model in self._session.scalars(stmt).all()]

    def get_default_for_organization(self, organization_id: UUID) -> SmtpAccount | None:
        stmt = select(SmtpAccountModel).where(
            SmtpAccountModel.organization_id == organization_id,
            SmtpAccountModel.is_default.is_(True),
            SmtpAccountModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        return model_to_entity(model) if model is not None else None

    def clear_default_for_organization(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID | None = None,
    ) -> None:
        stmt = select(SmtpAccountModel).where(
            SmtpAccountModel.organization_id == organization_id,
            SmtpAccountModel.is_default.is_(True),
            SmtpAccountModel.deleted_at.is_(None),
        )
        if exclude_account_id is not None:
            stmt = stmt.where(SmtpAccountModel.id != exclude_account_id)
        for model in self._session.scalars(stmt).all():
            model.is_default = False
