from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosureExecutionModel,
    OrganizationClosureExportPlanModel,
    OrganizationClosurePackageModel,
)
from app.modules.quote_templates.infrastructure.models import (
    QuoteTemplateModel,
    QuoteTemplateVersionModel,
)
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel


class SqlAlchemyOrganizationClosurePackageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_execution(
        self,
        organization_id: UUID,
        execution_id: UUID,
    ) -> OrganizationClosureExecutionModel | None:
        return self._session.scalar(
            select(OrganizationClosureExecutionModel).where(
                OrganizationClosureExecutionModel.organization_id == organization_id,
                OrganizationClosureExecutionModel.id == execution_id,
            )
        )

    def get_export_plan(
        self,
        organization_id: UUID,
        execution_id: UUID,
        schema_version: str,
    ) -> OrganizationClosureExportPlanModel | None:
        return self._session.scalar(
            select(OrganizationClosureExportPlanModel).where(
                OrganizationClosureExportPlanModel.organization_id == organization_id,
                OrganizationClosureExportPlanModel.closure_execution_id == execution_id,
                OrganizationClosureExportPlanModel.schema_version == schema_version,
            )
        )

    def get_package(
        self,
        organization_id: UUID,
        execution_id: UUID,
        schema_version: str,
    ) -> OrganizationClosurePackageModel | None:
        return self._session.scalar(
            select(OrganizationClosurePackageModel).where(
                OrganizationClosurePackageModel.organization_id == organization_id,
                OrganizationClosurePackageModel.closure_execution_id == execution_id,
                OrganizationClosurePackageModel.schema_version == schema_version,
            )
        )

    def add_package(self, package: OrganizationClosurePackageModel) -> None:
        self._session.add(package)

    def add_inventory(self, item: OrganizationClosureArtifactInventoryModel) -> None:
        self._session.add(item)

    def clear_inventory(self, package_id: UUID) -> None:
        self._session.execute(
            delete(OrganizationClosureArtifactInventoryModel).where(
                OrganizationClosureArtifactInventoryModel.package_id == package_id
            )
        )

    def list_inventory(
        self,
        organization_id: UUID,
        execution_id: UUID,
        package_id: UUID,
    ) -> tuple[OrganizationClosureArtifactInventoryModel, ...]:
        stmt = (
            select(OrganizationClosureArtifactInventoryModel)
            .where(
                OrganizationClosureArtifactInventoryModel.organization_id == organization_id,
                OrganizationClosureArtifactInventoryModel.closure_execution_id == execution_id,
                OrganizationClosureArtifactInventoryModel.package_id == package_id,
            )
            .order_by(OrganizationClosureArtifactInventoryModel.artifact_key)
        )
        return tuple(self._session.scalars(stmt).all())

    def list_scoped_ids(
        self,
        *,
        model: type,
        scope_model: type,
        organization_id: UUID,
        join_on: Any | None = None,
    ) -> tuple[Any, ...]:
        stmt = select(model.id)
        if join_on is not None:
            stmt = stmt.join(scope_model, join_on)
        stmt = stmt.where(scope_model.organization_id == organization_id).order_by(model.id)
        return tuple(self._session.scalars(stmt).all())

    def list_scoped_rows(
        self,
        *,
        model: type,
        scope_model: type,
        organization_id: UUID,
        join_on: Any | None = None,
    ) -> tuple[Any, ...]:
        stmt = select(model)
        if join_on is not None:
            stmt = stmt.join(scope_model, join_on)
        stmt = stmt.where(scope_model.organization_id == organization_id).order_by(model.id)
        return tuple(self._session.scalars(stmt).all())

    def list_quote_template_versions(
        self,
        organization_id: UUID,
    ) -> tuple[QuoteTemplateVersionModel, ...]:
        stmt = (
            select(QuoteTemplateVersionModel)
            .join(
                QuoteTemplateModel,
                QuoteTemplateVersionModel.template_id == QuoteTemplateModel.id,
            )
            .where(QuoteTemplateModel.organization_id == organization_id)
            .order_by(QuoteTemplateVersionModel.id)
        )
        return tuple(self._session.scalars(stmt).all())

    def list_import_batches_with_stored_bytes(
        self,
        organization_id: UUID,
    ) -> tuple[ImportBatchModel, ...]:
        stmt = (
            select(ImportBatchModel)
            .where(
                ImportBatchModel.organization_id == organization_id,
                ImportBatchModel.stored_file_content.is_not(None),
            )
            .order_by(ImportBatchModel.id)
        )
        return tuple(self._session.scalars(stmt).all())

    def list_scraper_runs(
        self,
        organization_id: UUID,
    ) -> tuple[ScraperRunHistoryModel, ...]:
        stmt = (
            select(ScraperRunHistoryModel)
            .where(ScraperRunHistoryModel.organization_id == organization_id)
            .order_by(ScraperRunHistoryModel.id)
        )
        return tuple(self._session.scalars(stmt).all())

    def flush(self) -> None:
        self._session.flush()
