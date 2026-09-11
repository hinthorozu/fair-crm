from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosureCredentialDispositionModel,
    OrganizationClosureCredentialEventModel,
    OrganizationClosureEventModel,
    OrganizationClosureExecutionModel,
    OrganizationClosureExportPlanModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.product_cleanup_models import (
    OrganizationClosureProductCleanupItemModel,
)


@dataclass(frozen=True, slots=True)
class LocalClosureEvidencePurgeCounts:
    credential_events: int
    credential_dispositions: int
    artifact_inventory: int
    packages: int
    export_plans: int
    product_cleanup_items: int
    closure_events: int
    closure_executions: int

    @property
    def total(self) -> int:
        return sum(
            (
                self.credential_events,
                self.credential_dispositions,
                self.artifact_inventory,
                self.packages,
                self.export_plans,
                self.product_cleanup_items,
                self.closure_events,
                self.closure_executions,
            )
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "credential_events": self.credential_events,
            "credential_dispositions": self.credential_dispositions,
            "artifact_inventory": self.artifact_inventory,
            "packages": self.packages,
            "export_plans": self.export_plans,
            "product_cleanup_items": self.product_cleanup_items,
            "closure_events": self.closure_events,
            "closure_executions": self.closure_executions,
        }


class SqlAlchemyOrganizationClosureEvidenceRetentionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_completed_execution(
        self,
        organization_id: UUID,
    ) -> OrganizationClosureExecutionModel | None:
        stmt = (
            select(OrganizationClosureExecutionModel)
            .where(
                OrganizationClosureExecutionModel.organization_id == organization_id,
                OrganizationClosureExecutionModel.status == "completed",
                OrganizationClosureExecutionModel.closed_at.is_not(None),
            )
            .order_by(OrganizationClosureExecutionModel.closed_at.asc())
            .limit(1)
        )
        return self._session.scalar(stmt)

    def purge_for_organization(
        self,
        organization_id: UUID,
    ) -> LocalClosureEvidencePurgeCounts:
        def purge(model: type, column) -> int:
            result = self._session.execute(delete(model).where(column == organization_id))
            return int(result.rowcount or 0)

        credential_events = purge(
            OrganizationClosureCredentialEventModel,
            OrganizationClosureCredentialEventModel.organization_id,
        )
        credential_dispositions = purge(
            OrganizationClosureCredentialDispositionModel,
            OrganizationClosureCredentialDispositionModel.organization_id,
        )
        artifact_inventory = purge(
            OrganizationClosureArtifactInventoryModel,
            OrganizationClosureArtifactInventoryModel.organization_id,
        )
        packages = purge(
            OrganizationClosurePackageModel,
            OrganizationClosurePackageModel.organization_id,
        )
        export_plans = purge(
            OrganizationClosureExportPlanModel,
            OrganizationClosureExportPlanModel.organization_id,
        )
        product_cleanup_items = purge(
            OrganizationClosureProductCleanupItemModel,
            OrganizationClosureProductCleanupItemModel.organization_id,
        )
        closure_events = purge(
            OrganizationClosureEventModel,
            OrganizationClosureEventModel.organization_id,
        )
        closure_executions = purge(
            OrganizationClosureExecutionModel,
            OrganizationClosureExecutionModel.organization_id,
        )
        self._session.flush()
        return LocalClosureEvidencePurgeCounts(
            credential_events=credential_events,
            credential_dispositions=credential_dispositions,
            artifact_inventory=artifact_inventory,
            packages=packages,
            export_plans=export_plans,
            product_cleanup_items=product_cleanup_items,
            closure_events=closure_events,
            closure_executions=closure_executions,
        )
