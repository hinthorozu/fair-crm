"""Delete selected customers from an analyze dataset (background job)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.system_admin.infrastructure.repositories.data_operation_dataset_repository import (
    SqlAlchemyDataOperationDatasetRepository,
)
from app.modules.system_admin.infrastructure.repositories.data_operation_run_repository import (
    SqlAlchemyDataOperationRunRepository,
)

DELETE_SELECTED_CUSTOMERS_OPERATION_KEY = "delete_selected_customers"


@dataclass(frozen=True)
class DeleteSelectedCustomersResult:
    deleted_count: int
    skipped_count: int
    failed_count: int
    removed_from_dataset_count: int

    def to_summary_json(self) -> dict[str, int | str]:
        return {
            "deleted_count": self.deleted_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "removed_from_dataset_count": self.removed_from_dataset_count,
        }


def _count_active_participations(
    session: Session,
    *,
    organization_id: UUID,
    customer_id: UUID,
) -> int:
    return (
        session.query(CustomerFairParticipationModel)
        .filter(
            CustomerFairParticipationModel.organization_id == organization_id,
            CustomerFairParticipationModel.customer_id == customer_id,
            CustomerFairParticipationModel.deleted_at.is_(None),
        )
        .count()
    )


def delete_selected_customers(
    db: Session,
    *,
    organization_id: UUID,
    parent_run_id: UUID,
    customer_ids: list[UUID],
) -> DeleteSelectedCustomersResult:
    dataset_repo = SqlAlchemyDataOperationDatasetRepository(db)
    run_repo = SqlAlchemyDataOperationRunRepository(db)

    dataset_customer_ids = dataset_repo.customer_ids_in_dataset(
        run_id=parent_run_id,
        organization_id=organization_id,
        customer_ids=customer_ids,
    )

    deleted = 0
    skipped = 0
    failed = 0
    removed_ids: list[UUID] = []
    now = datetime.now(tz=UTC)

    for customer_id in customer_ids:
        if customer_id not in dataset_customer_ids:
            failed += 1
            continue

        customer_model = db.get(CustomerModel, customer_id)
        if customer_model is None or customer_model.organization_id != organization_id:
            failed += 1
            continue

        if _count_active_participations(db, organization_id=organization_id, customer_id=customer_id) > 0:
            skipped += 1
            removed_ids.append(customer_id)
            continue

        try:
            db.delete(customer_model)
            db.flush()
            deleted += 1
            removed_ids.append(customer_id)
        except Exception:
            failed += 1

    removed_count = dataset_repo.remove_customer_rows(
        run_id=parent_run_id,
        organization_id=organization_id,
        customer_ids=removed_ids,
    )

    parent_run = run_repo.get_by_id(organization_id, parent_run_id)
    if parent_run and parent_run.summary_json is not None:
        summary = dict(parent_run.summary_json)
        total = int(summary.get("total_customers", 0))
        without = int(summary.get("customers_without_fair", 0))
        with_fair = int(summary.get("customers_with_fair", 0))
        summary["total_customers"] = max(0, total - deleted)
        summary["customers_without_fair"] = max(0, without - removed_count)
        summary["customers_with_fair"] = with_fair + skipped
        parent_run.summary_json = summary
        parent_run.updated_at = now
        run_repo.update(parent_run)

    return DeleteSelectedCustomersResult(
        deleted_count=deleted,
        skipped_count=skipped,
        failed_count=failed,
        removed_from_dataset_count=removed_count,
    )
