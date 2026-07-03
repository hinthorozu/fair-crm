"""Admin-selected field grouping for Duplicate Customer Analysis dataset operations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.orm import Session, load_only

from app.modules.customers.domain.communication_entities import CustomerCommunications
from app.modules.customers.domain.services.normalizers import (
    compute_normalized_name,
    normalize_email,
    normalize_phone,
    normalize_website,
)
from app.modules.customers.application.customer_duplicate_eligibility import (
    exclude_merge_deleted_customers,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
GroupByField = Literal["company_name", "email", "website", "phone"]

GROUP_BY_FIELDS: frozenset[str] = frozenset({"company_name", "email", "website", "phone"})

_COMMUNICATION_GROUP_FIELDS = frozenset({"email", "website", "phone"})


@dataclass(frozen=True)
class FieldGroupMemberRow:
    customer_id: UUID
    group_key: str
    fair_count: int
    first_fair_name: str | None


@dataclass(frozen=True)
class FieldGroupAnalysisSummary:
    dataset_kind: str
    group_by: str
    total_customers: int
    duplicate_groups: int
    customers_in_duplicate_groups: int

    def to_json(self) -> dict[str, int | str]:
        return {
            "dataset_kind": self.dataset_kind,
            "group_by": self.group_by,
            "total_customers": self.total_customers,
            "duplicate_groups": self.duplicate_groups,
            "customers_in_duplicate_groups": self.customers_in_duplicate_groups,
        }


def grouping_keys_for_customer(
    group_by: GroupByField,
    model: CustomerModel,
    communications: CustomerCommunications | None,
) -> list[str]:
    if group_by == "company_name":
        key = compute_normalized_name(
            display_name=model.display_name,
            legal_name=model.legal_name,
        )
        return [key] if key else []

    if communications is None:
        return []

    if group_by == "email":
        keys: list[str] = []
        seen: set[str] = set()
        for item in communications.emails:
            key = normalize_email(item.email)
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
        return keys

    if group_by == "website":
        keys: list[str] = []
        seen: set[str] = set()
        for item in communications.websites:
            key = normalize_website(item.website)
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
        return keys

    if group_by == "phone":
        keys: list[str] = []
        seen: set[str] = set()
        for item in communications.phones:
            key = normalize_phone(item.phone)
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
        return keys

    return []


def _load_fair_metadata(session: Session) -> tuple[dict[UUID, int], dict[UUID, str | None]]:
    fair_counts: dict[UUID, int] = {
        customer_id: count
        for customer_id, count in session.query(
            CustomerFairParticipationModel.customer_id,
            func.count(CustomerFairParticipationModel.id),
        )
        .filter(CustomerFairParticipationModel.deleted_at.is_(None))
        .group_by(CustomerFairParticipationModel.customer_id)
        .all()
    }

    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        first_fair: dict[UUID, str | None] = {
            customer_id: fair_name
            for customer_id, fair_name in session.execute(
                text(
                    """
                    SELECT DISTINCT ON (p.customer_id) p.customer_id, f.name
                    FROM crm_customer_fair_participations p
                    JOIN crm_fairs f ON f.id = p.fair_id
                    WHERE p.deleted_at IS NULL
                    ORDER BY p.customer_id, p.created_at ASC
                    """
                )
            )
        }
    else:
        from app.modules.fairs.infrastructure.persistence.models import FairModel

        first_fair = {}
        rows = (
            session.query(
                CustomerFairParticipationModel.customer_id,
                CustomerFairParticipationModel.created_at,
                FairModel.name,
            )
            .join(FairModel, FairModel.id == CustomerFairParticipationModel.fair_id)
            .filter(CustomerFairParticipationModel.deleted_at.is_(None))
            .order_by(
                CustomerFairParticipationModel.customer_id.asc(),
                CustomerFairParticipationModel.created_at.asc(),
            )
            .all()
        )
        for customer_id, _created_at, fair_name in rows:
            if customer_id not in first_fair:
                first_fair[customer_id] = fair_name

    return fair_counts, first_fair


def analyze_customer_groups_by_field(
    session: Session,
    *,
    organization_id: UUID,
    group_by: GroupByField,
    company_name_fuzzy_matching: bool = False,
) -> tuple[FieldGroupAnalysisSummary, list[FieldGroupMemberRow]]:
    if group_by not in GROUP_BY_FIELDS:
        raise ValueError(f"Unsupported group_by field: {group_by}")

    models = (
        exclude_merge_deleted_customers(
            session.query(CustomerModel)
            .options(
                load_only(
                    CustomerModel.id,
                    CustomerModel.display_name,
                    CustomerModel.legal_name,
                    CustomerModel.normalized_name,
                )
            )
            .filter(CustomerModel.organization_id == organization_id)
        )
        .order_by(CustomerModel.display_name.asc(), CustomerModel.id.asc())
        .all()
    )
    fair_counts, first_fair_names = _load_fair_metadata(session)

    communications: dict[UUID, CustomerCommunications] = {}
    if group_by in _COMMUNICATION_GROUP_FIELDS:
        customer_ids = [model.id for model in models]
        communications = SqlAlchemyCustomerCommunicationRepository(session).load_for_customers(
            customer_ids,
        )

    buckets: dict[str, dict[UUID, CustomerModel]] = defaultdict(dict)
    for model in models:
        comm = communications.get(model.id)
        for key in grouping_keys_for_customer(group_by, model, comm):
            buckets[key][model.id] = model

    if group_by == "company_name" and company_name_fuzzy_matching:
        from app.modules.customers.application.duplicate_company_name_grouping import (
            merge_similar_company_name_buckets,
        )

        buckets = merge_similar_company_name_buckets(buckets)

    member_rows: list[FieldGroupMemberRow] = []
    group_count = 0
    for group_key, members_by_id in sorted(buckets.items(), key=lambda item: item[0]):
        if len(members_by_id) < 2:
            continue
        group_count += 1
        members = sorted(
            members_by_id.values(),
            key=lambda model: (model.display_name.lower(), str(model.id)),
        )
        for model in members:
            member_rows.append(
                FieldGroupMemberRow(
                    customer_id=model.id,
                    group_key=group_key,
                    fair_count=fair_counts.get(model.id, 0),
                    first_fair_name=first_fair_names.get(model.id),
                )
            )

    summary = FieldGroupAnalysisSummary(
        dataset_kind="duplicate_customer_groups",
        group_by=group_by,
        total_customers=len(models),
        duplicate_groups=group_count,
        customers_in_duplicate_groups=len(member_rows),
    )
    return summary, member_rows
