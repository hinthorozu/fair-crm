"""Shared duplicate customer group analysis used by maintenance scripts and data operations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel

CLASS_STRONG = "strong_duplicate"
CLASS_PROBABLE = "probable_duplicate"
CLASS_POSSIBLE = "possible_duplicate"
CLASS_MANUAL = "manual_review"


@dataclass
class CustomerRecord:
    id: UUID
    organization_id: UUID
    company_name: str
    normalized_company_name: str
    phone: str | None
    email: str | None
    website: str | None
    city: str | None
    country: str | None
    status: str
    created_at: datetime
    norm_key: str
    email_key: str | None
    phone_key: str | None
    fair_count: int = 0
    first_fair_name: str | None = None


@dataclass
class EdgeInfo:
    score: int
    reason: str


class UnionFind:
    def __init__(self, ids: list[UUID]) -> None:
        self.parent = {customer_id: customer_id for customer_id in ids}

    def find(self, customer_id: UUID) -> UUID:
        parent = self.parent[customer_id]
        if parent != customer_id:
            self.parent[customer_id] = self.find(parent)
        return self.parent[customer_id]

    def union(self, left: UUID, right: UUID) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


@dataclass
class GroupBuilder:
    union_find: UnionFind
    edge_scores: dict[UUID, dict[UUID, EdgeInfo]] = field(default_factory=dict)

    def link(self, left: UUID, right: UUID, *, score: int, reason: str) -> None:
        if left == right:
            return
        self.union_find.union(left, right)
        info = EdgeInfo(score=score, reason=reason)
        self.edge_scores.setdefault(left, {})[right] = info
        self.edge_scores.setdefault(right, {})[left] = info


@dataclass(frozen=True)
class DuplicateGroupMemberRow:
    customer_id: UUID
    duplicate_group_key: str
    match_score: int | None
    duplicate_reason: str
    fair_count: int
    first_fair_name: str | None


@dataclass(frozen=True)
class DuplicateGroupAnalysisSummary:
    dataset_kind: str
    total_customers: int
    duplicate_groups: int
    customers_in_duplicate_groups: int

    def to_json(self) -> dict[str, int | str]:
        return {
            "dataset_kind": self.dataset_kind,
            "total_customers": self.total_customers,
            "duplicate_groups": self.duplicate_groups,
            "customers_in_duplicate_groups": self.customers_in_duplicate_groups,
        }


def normalize_email_key(email: str | None) -> str | None:
    if not email:
        return None
    from app.shared.email import normalize_email_field

    try:
        return normalize_email_field(email) or None
    except ValueError:
        lowered = email.strip().lower()
        return lowered or None


def normalize_phone_key(phone: str | None) -> str | None:
    if not phone:
        return None
    from app.modules.customers.domain.services.normalizers import normalize_phone

    digits = normalize_phone(phone)
    return digits or None


def customer_norm_key(company_name: str, normalized_company_name: str) -> str:
    from app.modules.imports.domain.services.company_name_normalizer import (
        normalize_import_company_name,
    )

    norm = normalize_import_company_name(company_name)
    if norm:
        return norm
    return normalize_import_company_name(normalized_company_name)


def classify_score(score: int) -> str:
    from app.modules.imports.domain.services.company_name_matcher import (
        MATCH_SCORE_MIN,
        MATCH_SCORE_POSSIBLE,
        MATCH_SCORE_STRONG,
    )

    if score >= MATCH_SCORE_STRONG:
        return CLASS_STRONG
    if score >= MATCH_SCORE_POSSIBLE:
        return CLASS_PROBABLE
    if score >= MATCH_SCORE_MIN:
        return CLASS_POSSIBLE
    return CLASS_MANUAL


def best_edge_in_group(
    customer_id: UUID,
    member_ids: set[UUID],
    edge_scores: dict[UUID, dict[UUID, EdgeInfo]],
) -> EdgeInfo:
    neighbors = edge_scores.get(customer_id, {})
    best = EdgeInfo(score=0, reason="transitive_group_member")
    for other_id in member_ids:
        if other_id == customer_id:
            continue
        edge = neighbors.get(other_id)
        if edge is None:
            continue
        if edge.score > best.score:
            best = edge
    return best


def load_fair_metadata(session: Session) -> tuple[dict[UUID, int], dict[UUID, str | None]]:
    fair_counts: dict[UUID, int] = defaultdict(int)
    first_fair: dict[UUID, tuple[datetime, str]] = {}

    rows = (
        session.query(
            CustomerFairParticipationModel.customer_id,
            CustomerFairParticipationModel.created_at,
            FairModel.name,
        )
        .join(FairModel, FairModel.id == CustomerFairParticipationModel.fair_id)
        .order_by(
            CustomerFairParticipationModel.customer_id.asc(),
            CustomerFairParticipationModel.created_at.asc(),
        )
        .all()
    )
    for customer_id, created_at, fair_name in rows:
        fair_counts[customer_id] += 1
        if customer_id not in first_fair:
            first_fair[customer_id] = (created_at, fair_name)

    first_fair_names = {customer_id: value[1] for customer_id, value in first_fair.items()}
    return dict(fair_counts), first_fair_names


def build_org_groups(records: list[CustomerRecord]) -> tuple[dict[UUID, list[UUID]], GroupBuilder]:
    from app.modules.customers.domain.entities import Customer
    from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
    from app.modules.imports.domain.services.duplicate_detector import (
        CustomerMatchIndex,
        find_customer_match,
    )

    ids = [record.id for record in records]
    builder = GroupBuilder(union_find=UnionFind(ids))

    def union_bucket(
        bucket: dict[str, list[UUID]],
        *,
        score: int,
        reason: str,
    ) -> None:
        for members in bucket.values():
            if len(members) < 2:
                continue
            anchor = members[0]
            for other in members[1:]:
                builder.link(anchor, other, score=score, reason=reason)

    norm_bucket: dict[str, list[UUID]] = defaultdict(list)
    email_bucket: dict[str, list[UUID]] = defaultdict(list)
    phone_bucket: dict[str, list[UUID]] = defaultdict(list)

    for record in records:
        if record.norm_key:
            norm_bucket[record.norm_key].append(record.id)
        if record.email_key:
            email_bucket[record.email_key].append(record.id)
        if record.phone_key:
            phone_bucket[record.phone_key].append(record.id)

    union_bucket(norm_bucket, score=100, reason="normalized_exact")
    union_bucket(email_bucket, score=100, reason="email_exact_match")
    union_bucket(phone_bucket, score=100, reason="phone_exact_match")

    entities = [
        Customer(
            id=record.id,
            organization_id=record.organization_id,
            display_name=record.company_name,
            legal_name=None,
            trade_name=None,
            normalized_name=record.normalized_company_name,
            customer_type=CustomerType.OTHER,
            status=CustomerStatus(record.status),
            website=record.website,
            phone=record.phone,
            email=record.email,
            tax_number=None,
            tax_office=None,
            country=record.country,
            city=record.city,
            district=None,
            address=None,
            description=None,
            source=CustomerSource.MANUAL,
            created_at=record.created_at,
            updated_at=record.created_at,
            deleted_at=None,
        )
        for record in records
    ]
    match_index = CustomerMatchIndex.build(entities)

    for record in records:
        if not record.norm_key:
            continue
        match = find_customer_match(
            record.norm_key,
            match_index,
            raw_company_name=record.company_name,
        )
        if match is None or match.customer_id == record.id:
            continue
        reason = match.explanation or match.reason
        builder.link(record.id, match.customer_id, score=match.confidence, reason=reason)

    grouped: dict[UUID, list[UUID]] = defaultdict(list)
    for customer_id in ids:
        grouped[builder.union_find.find(customer_id)].append(customer_id)

    duplicate_groups = {
        root: sorted(members) for root, members in grouped.items() if len(members) >= 2
    }
    return duplicate_groups, builder


def analyze_duplicate_groups_for_organization(
    session: Session,
    *,
    organization_id: UUID,
) -> tuple[DuplicateGroupAnalysisSummary, list[DuplicateGroupMemberRow]]:
    fair_counts, first_fair_names = load_fair_metadata(session)
    models = (
        session.query(CustomerModel)
        .filter(CustomerModel.organization_id == organization_id)
        .order_by(CustomerModel.display_name.asc(), CustomerModel.id.asc())
        .all()
    )
    summaries = SqlAlchemyCustomerCommunicationRepository(session).load_list_summaries(
        [model.id for model in models],
    )

    records: list[CustomerRecord] = []
    for model in models:
        summary = summaries.get(model.id)
        phone = summary.phone if summary else None
        email = summary.email if summary else None
        website = summary.website if summary else None
        records.append(
            CustomerRecord(
                id=model.id,
                organization_id=model.organization_id,
                company_name=model.display_name,
                normalized_company_name=model.normalized_name,
                phone=phone,
                email=email,
                website=website,
                city=model.city,
                country=model.country,
                status=model.status,
                created_at=model.created_at,
                norm_key=customer_norm_key(model.display_name, model.normalized_name),
                email_key=normalize_email_key(email),
                phone_key=normalize_phone_key(phone),
                fair_count=fair_counts.get(model.id, 0),
                first_fair_name=first_fair_names.get(model.id),
            )
        )

    org_groups, builder = build_org_groups(records)
    record_map = {record.id: record for record in records}

    member_rows: list[DuplicateGroupMemberRow] = []
    group_serial = 0
    for _root, members in sorted(
        org_groups.items(),
        key=lambda item: (len(item[1]), str(item[1][0])),
        reverse=True,
    ):
        group_serial += 1
        group_key = f"dup_grp_{group_serial:05d}"
        member_set = set(members)
        for customer_id in members:
            record = record_map[customer_id]
            edge = best_edge_in_group(customer_id, member_set, builder.edge_scores)
            member_rows.append(
                DuplicateGroupMemberRow(
                    customer_id=customer_id,
                    duplicate_group_key=group_key,
                    match_score=edge.score if edge.score > 0 else None,
                    duplicate_reason=edge.reason,
                    fair_count=record.fair_count,
                    first_fair_name=record.first_fair_name,
                )
            )

    summary = DuplicateGroupAnalysisSummary(
        dataset_kind="duplicate_customer_groups",
        total_customers=len(records),
        duplicate_groups=len(org_groups),
        customers_in_duplicate_groups=len(member_rows),
    )
    return summary, member_rows
