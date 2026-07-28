from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.modules.customers.application.customer_duplicate_eligibility import (
    exclude_merge_deleted_customers,
)
from app.modules.customers.application.customer_field_grouping import (
    GroupByField,
    analyze_customer_groups_by_field,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.system_admin.infrastructure.repositories.data_operation_dataset_repository import (
    DuplicateDatasetRowInput,
    SqlAlchemyDataOperationDatasetRepository,
)


@dataclass(frozen=True)
class CustomersWithoutFairDatasetSummary:
    dataset_kind: str
    total_customers: int
    customers_with_fair: int
    customers_without_fair: int

    def to_json(self) -> dict[str, int | str]:
        return {
            "dataset_kind": self.dataset_kind,
            "total_customers": self.total_customers,
            "customers_with_fair": self.customers_with_fair,
            "customers_without_fair": self.customers_without_fair,
        }


def _live_customer_query(session: Session, *, organization_id: UUID):
    """Same live customer scope as customer list/detail: not soft/merge-deleted."""
    return exclude_merge_deleted_customers(
        session.query(CustomerModel).filter(
            CustomerModel.organization_id == organization_id,
            CustomerModel.deleted_at.is_(None),
        )
    )


def _live_participation_join():
    """Match Customer Detail / participation repository: deleted_at IS NULL."""
    return and_(
        CustomerModel.id == CustomerFairParticipationModel.customer_id,
        CustomerFairParticipationModel.organization_id == CustomerModel.organization_id,
        CustomerFairParticipationModel.deleted_at.is_(None),
    )


def build_customers_without_fair_dataset(
    session: Session,
    *,
    organization_id: UUID,
    run_id: UUID,
) -> CustomersWithoutFairDatasetSummary:
    total_customers = _live_customer_query(session, organization_id=organization_id).count()

    assigned_customer_count = (
        exclude_merge_deleted_customers(
            session.query(func.count(func.distinct(CustomerModel.id)))
            .select_from(CustomerModel)
            .join(CustomerFairParticipationModel, _live_participation_join())
            .filter(
                CustomerModel.organization_id == organization_id,
                CustomerModel.deleted_at.is_(None),
            )
        ).scalar()
        or 0
    )

    unassigned_ids = [
        row[0]
        for row in (
            exclude_merge_deleted_customers(
                session.query(CustomerModel.id)
                .outerjoin(CustomerFairParticipationModel, _live_participation_join())
                .filter(
                    CustomerModel.organization_id == organization_id,
                    CustomerModel.deleted_at.is_(None),
                    CustomerFairParticipationModel.id.is_(None),
                )
            )
            .order_by(CustomerModel.display_name.asc(), CustomerModel.id.asc())
            .all()
        )
    ]

    dataset_repo = SqlAlchemyDataOperationDatasetRepository(session)
    dataset_repo.replace_customer_rows(
        run_id=run_id,
        organization_id=organization_id,
        customer_ids=unassigned_ids,
    )

    return CustomersWithoutFairDatasetSummary(
        dataset_kind="customers_without_fair",
        total_customers=total_customers,
        customers_with_fair=assigned_customer_count,
        customers_without_fair=len(unassigned_ids),
    )


@dataclass(frozen=True)
class DuplicateCustomerGroupsDatasetSummary:
    dataset_kind: str
    group_by: str
    total_customers: int
    duplicate_groups: int
    customers_in_duplicate_groups: int
    fair_id: str | None = None
    fair_name: str | None = None

    def to_json(self) -> dict[str, int | str | None]:
        payload: dict[str, int | str | None] = {
            "dataset_kind": self.dataset_kind,
            "group_by": self.group_by,
            "total_customers": self.total_customers,
            "duplicate_groups": self.duplicate_groups,
            "customers_in_duplicate_groups": self.customers_in_duplicate_groups,
        }
        if self.fair_id is not None:
            payload["fair_id"] = self.fair_id
        if self.fair_name is not None:
            payload["fair_name"] = self.fair_name
        return payload


def build_duplicate_customer_groups_dataset(
    session: Session,
    *,
    organization_id: UUID,
    run_id: UUID,
    group_by: GroupByField,
    fair_id: UUID | None = None,
) -> DuplicateCustomerGroupsDatasetSummary:
    summary, member_rows = analyze_customer_groups_by_field(
        session,
        organization_id=organization_id,
        group_by=group_by,
        company_name_fuzzy_matching=(group_by == "company_name"),
        fair_id=fair_id,
    )

    dataset_repo = SqlAlchemyDataOperationDatasetRepository(session)
    dataset_repo.replace_duplicate_customer_rows(
        run_id=run_id,
        organization_id=organization_id,
        group_by=group_by,
        rows=[
            DuplicateDatasetRowInput(
                customer_id=row.customer_id,
                group_key=row.group_key,
                fair_count=row.fair_count,
                first_fair_name=row.first_fair_name,
                match_score=row.match_score,
                duplicate_reason=row.duplicate_reason,
            )
            for row in member_rows
        ],
    )

    return DuplicateCustomerGroupsDatasetSummary(
        dataset_kind=summary.dataset_kind,
        group_by=summary.group_by,
        total_customers=summary.total_customers,
        duplicate_groups=summary.duplicate_groups,
        customers_in_duplicate_groups=summary.customers_in_duplicate_groups,
        fair_id=summary.fair_id,
        fair_name=summary.fair_name,
    )
