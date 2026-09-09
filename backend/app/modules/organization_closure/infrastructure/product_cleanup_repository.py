from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.modules.email_accounts.infrastructure.persistence.models import EmailAccountModel
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosureCredentialDispositionModel,
    OrganizationClosureExecutionModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.product_cleanup_models import (
    OrganizationClosureProductCleanupItemModel,
)


class SqlAlchemyOrganizationClosureProductCleanupRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_execution(
        self, organization_id: UUID, execution_id: UUID
    ) -> OrganizationClosureExecutionModel | None:
        stmt = select(OrganizationClosureExecutionModel).where(
            OrganizationClosureExecutionModel.organization_id == organization_id,
            OrganizationClosureExecutionModel.id == execution_id,
        )
        return self._session.scalars(stmt).one_or_none()

    def get_package(
        self, organization_id: UUID, execution_id: UUID, schema_version: str
    ) -> OrganizationClosurePackageModel | None:
        stmt = select(OrganizationClosurePackageModel).where(
            OrganizationClosurePackageModel.organization_id == organization_id,
            OrganizationClosurePackageModel.closure_execution_id == execution_id,
            OrganizationClosurePackageModel.schema_version == schema_version,
        )
        return self._session.scalars(stmt).one_or_none()

    def list_inventory(
        self, organization_id: UUID, execution_id: UUID, package_id: UUID
    ) -> tuple[OrganizationClosureArtifactInventoryModel, ...]:
        stmt = (
            select(OrganizationClosureArtifactInventoryModel)
            .where(
                OrganizationClosureArtifactInventoryModel.organization_id == organization_id,
                OrganizationClosureArtifactInventoryModel.closure_execution_id == execution_id,
                OrganizationClosureArtifactInventoryModel.package_id == package_id,
            )
            .order_by(OrganizationClosureArtifactInventoryModel.artifact_key.asc())
        )
        return tuple(self._session.scalars(stmt).all())

    def list_credentials(
        self, organization_id: UUID, execution_id: UUID
    ) -> tuple[OrganizationClosureCredentialDispositionModel, ...]:
        stmt = (
            select(OrganizationClosureCredentialDispositionModel)
            .where(
                OrganizationClosureCredentialDispositionModel.organization_id == organization_id,
                OrganizationClosureCredentialDispositionModel.closure_execution_id == execution_id,
            )
            .order_by(OrganizationClosureCredentialDispositionModel.email_account_id.asc())
        )
        return tuple(self._session.scalars(stmt).all())

    def list_email_account_ids(self, organization_id: UUID) -> tuple[UUID, ...]:
        stmt = (
            select(EmailAccountModel.id)
            .where(EmailAccountModel.organization_id == organization_id)
            .order_by(EmailAccountModel.id.asc())
        )
        return tuple(self._session.scalars(stmt).all())

    def list_items(
        self, organization_id: UUID, execution_id: UUID, policy_version: str
    ) -> tuple[OrganizationClosureProductCleanupItemModel, ...]:
        stmt = (
            select(OrganizationClosureProductCleanupItemModel)
            .where(
                OrganizationClosureProductCleanupItemModel.organization_id == organization_id,
                OrganizationClosureProductCleanupItemModel.closure_execution_id == execution_id,
                OrganizationClosureProductCleanupItemModel.policy_version == policy_version,
            )
            .order_by(
                OrganizationClosureProductCleanupItemModel.sequence.asc(),
                OrganizationClosureProductCleanupItemModel.class_key.asc(),
            )
        )
        return tuple(self._session.scalars(stmt).all())

    def add_item(self, item: OrganizationClosureProductCleanupItemModel) -> None:
        self._session.add(item)

    def count_direct(self, model: type, organization_id: UUID) -> int:
        stmt = select(func.count()).select_from(model).where(
            model.organization_id == organization_id
        )
        return int(self._session.scalar(stmt) or 0)

    def delete_direct(self, model: type, organization_id: UUID) -> None:
        self._session.execute(delete(model).where(model.organization_id == organization_id))

    def scoped_ids(self, model: type, organization_id: UUID) -> tuple[UUID, ...]:
        stmt = select(model.id).where(model.organization_id == organization_id)
        return tuple(self._session.scalars(stmt).all())

    def count_where(self, model: type, *conditions: Any) -> int:
        stmt = select(func.count()).select_from(model).where(*conditions)
        return int(self._session.scalar(stmt) or 0)

    def delete_where(self, model: type, *conditions: Any) -> None:
        self._session.execute(delete(model).where(*conditions))

    def update_where(self, model: type, values: dict[str, Any], *conditions: Any) -> None:
        self._session.execute(update(model).where(*conditions).values(**values))

    def nested(self) -> AbstractContextManager[Any]:
        return self._session.begin_nested()

    def flush(self) -> None:
        self._session.flush()
