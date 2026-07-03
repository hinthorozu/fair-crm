"""Assign selected customers from an analyze dataset to a fair (background job)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.participations.application.validators import (
    ensure_customer_for_participation,
    ensure_fair_for_participation,
)
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.exceptions import DuplicateParticipationError
from app.modules.participations.domain.value_objects import ParticipationStatus
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.modules.system_admin.infrastructure.repositories.data_operation_dataset_repository import (
    SqlAlchemyDataOperationDatasetRepository,
)
from app.modules.system_admin.infrastructure.repositories.data_operation_run_repository import (
    SqlAlchemyDataOperationRunRepository,
)

ASSIGN_CUSTOMERS_TO_FAIR_OPERATION_KEY = "assign_customers_to_fair"
ANALYZE_CUSTOMERS_WITHOUT_FAIR_OPERATION_KEY = "analyze_customers_without_fair"


@dataclass(frozen=True)
class AssignCustomersToFairResult:
    assigned_count: int
    skipped_count: int
    failed_count: int
    removed_from_dataset_count: int

    def to_summary_json(self) -> dict[str, int | str]:
        return {
            "assigned_count": self.assigned_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "removed_from_dataset_count": self.removed_from_dataset_count,
        }


def assign_customers_to_fair(
    db: Session,
    *,
    organization_id: UUID,
    parent_run_id: UUID,
    fair_id: UUID,
    customer_ids: list[UUID],
) -> AssignCustomersToFairResult:
    customer_repo = SqlAlchemyCustomerRepository(db)
    fair_repo = SqlAlchemyFairRepository(db)
    participation_repo = SqlAlchemyParticipationRepository(db)
    dataset_repo = SqlAlchemyDataOperationDatasetRepository(db)
    run_repo = SqlAlchemyDataOperationRunRepository(db)

    ensure_fair_for_participation(fair_repo, organization_id, fair_id)

    dataset_customer_ids = dataset_repo.customer_ids_in_dataset(
        run_id=parent_run_id,
        organization_id=organization_id,
        customer_ids=customer_ids,
    )

    assigned = 0
    skipped = 0
    failed = 0
    removed_ids: list[UUID] = []
    now = datetime.now(tz=UTC)

    for customer_id in customer_ids:
        if customer_id not in dataset_customer_ids:
            failed += 1
            continue
        try:
            ensure_customer_for_participation(customer_repo, organization_id, customer_id)
            if participation_repo.exists_active(organization_id, customer_id, fair_id):
                skipped += 1
                removed_ids.append(customer_id)
                continue

            participation = CustomerFairParticipation.create(
                organization_id=organization_id,
                customer_id=customer_id,
                fair_id=fair_id,
                participation_status=ParticipationStatus.EXHIBITOR,
                now=now,
            )
            participation_repo.add(participation)
            assigned += 1
            removed_ids.append(customer_id)
        except DuplicateParticipationError:
            skipped += 1
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
        without = int(summary.get("customers_without_fair", 0))
        with_fair = int(summary.get("customers_with_fair", 0))
        summary["customers_without_fair"] = max(0, without - removed_count)
        summary["customers_with_fair"] = with_fair + assigned
        parent_run.summary_json = summary
        parent_run.updated_at = now
        run_repo.update(parent_run)

    return AssignCustomersToFairResult(
        assigned_count=assigned,
        skipped_count=skipped,
        failed_count=failed,
        removed_from_dataset_count=removed_count,
    )
