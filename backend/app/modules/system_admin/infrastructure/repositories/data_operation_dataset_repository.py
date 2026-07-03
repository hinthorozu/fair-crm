from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Query, Session

from app.core.pagination import build_order_clause, normalize_page_params
from app.modules.customers.application.customer_duplicate_eligibility import (
    exclude_merge_deleted_customers,
)
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.mappers import model_to_entity
from app.modules.customers.infrastructure.persistence.communication_query_helpers import (
    email_search_exists,
    phone_search_exists,
    primary_email_subquery,
    primary_phone_subquery,
    primary_website_subquery,
    website_search_exists,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.system_admin.application.duplicate_group_review import (
    GroupMemberSnapshot,
    pick_suggested_winner_customer,
)
from app.modules.system_admin.infrastructure.persistence.models import SystemDataOperationDatasetRowModel

DATASET_CUSTOMER_SORT_FIELDS = {
    "created_at": CustomerModel.created_at,
    "updated_at": CustomerModel.updated_at,
    "name": func.lower(CustomerModel.display_name),
    "display_name": func.lower(CustomerModel.display_name),
    "company_name": func.lower(CustomerModel.display_name),
    "legal_name": func.lower(CustomerModel.legal_name),
    "trade_name": func.lower(CustomerModel.trade_name),
    "country": CustomerModel.country,
    "city": CustomerModel.city,
    "email": primary_email_subquery(),
    "website": primary_website_subquery(),
    "status": CustomerModel.status,
    "customer_type": CustomerModel.customer_type,
    "phone": primary_phone_subquery(),
}

DATASET_CUSTOMER_SEARCH_FIELDS = (
    CustomerModel.display_name,
    CustomerModel.normalized_name,
    CustomerModel.legal_name,
    CustomerModel.trade_name,
    CustomerModel.country,
    CustomerModel.city,
    CustomerModel.district,
    CustomerModel.address,
)

BULK_INSERT_BATCH_SIZE = 1000


def _dedupe_duplicate_dataset_rows(
    rows: list[DuplicateDatasetRowInput],
) -> list[DuplicateDatasetRowInput]:
    seen: set[tuple[UUID, str]] = set()
    deduped: list[DuplicateDatasetRowInput] = []
    for row in rows:
        key = (row.customer_id, row.group_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


@dataclass(frozen=True)
class DatasetCustomerListResult:
    items: list[Customer]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class DuplicateDatasetRowInput:
    customer_id: UUID
    group_key: str
    fair_count: int
    first_fair_name: str | None


@dataclass(frozen=True)
class DatasetDuplicateCustomerItem:
    customer: Customer
    group_key: str
    group_by: str | None
    fair_count: int
    first_fair_name: str | None


@dataclass(frozen=True)
class DatasetDuplicateCustomerListResult:
    items: list[DatasetDuplicateCustomerItem]
    page: int
    page_size: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class DuplicateGroupParticipationDetail:
    fair_name: str
    fair_year: int | None
    hall: str | None
    stand: str | None


@dataclass(frozen=True)
class DatasetDuplicateGroupSummary:
    group_key: str
    group_by: str
    customer_count: int
    fair_count: int
    fair_names: list[str]
    suggested_winner_customer_id: UUID
    suggested_winner_company_name: str
    created_at_min: datetime
    created_at_max: datetime
    customer_names: list[str]


@dataclass(frozen=True)
class DatasetDuplicateGroupListResult:
    items: list[DatasetDuplicateGroupSummary]
    page: int
    page_size: int
    total: int
    total_pages: int
    group_by: str | None
    live_duplicate_groups: int
    live_customers_in_duplicate_groups: int


@dataclass(frozen=True)
class DuplicateGroupCustomerDetail:
    customer: Customer
    participations: list[DuplicateGroupParticipationDetail]


@dataclass(frozen=True)
class DatasetDuplicateGroupDetail:
    group_key: str
    group_by: str
    customers: list[DuplicateGroupCustomerDetail]


DATASET_DUPLICATE_SORT_FIELDS = {
    **DATASET_CUSTOMER_SORT_FIELDS,
    "group_key": SystemDataOperationDatasetRowModel.duplicate_group_key,
    "duplicate_group_key": SystemDataOperationDatasetRowModel.duplicate_group_key,
    "duplicate_group": SystemDataOperationDatasetRowModel.duplicate_group_key,
    "fair_count": SystemDataOperationDatasetRowModel.fair_count,
    "first_fair_name": SystemDataOperationDatasetRowModel.first_fair_name,
    "first_fair": SystemDataOperationDatasetRowModel.first_fair_name,
}

DATASET_DUPLICATE_SEARCH_FIELDS = DATASET_CUSTOMER_SEARCH_FIELDS + (
    SystemDataOperationDatasetRowModel.duplicate_group_key,
    SystemDataOperationDatasetRowModel.first_fair_name,
)


class SqlAlchemyDataOperationDatasetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_customer_rows(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        customer_ids: list[UUID],
    ) -> None:
        self._session.query(SystemDataOperationDatasetRowModel).filter(
            SystemDataOperationDatasetRowModel.run_id == run_id,
            SystemDataOperationDatasetRowModel.organization_id == organization_id,
        ).delete(synchronize_session=False)

        now = datetime.now(tz=UTC)
        for offset in range(0, len(customer_ids), BULK_INSERT_BATCH_SIZE):
            batch = customer_ids[offset : offset + BULK_INSERT_BATCH_SIZE]
            self._session.bulk_save_objects(
                [
                    SystemDataOperationDatasetRowModel(
                        id=uuid4(),
                        run_id=run_id,
                        organization_id=organization_id,
                        entity_kind="customer",
                        entity_id=customer_id,
                        created_at=now,
                    )
                    for customer_id in batch
                ]
            )
        self._session.flush()

    def replace_duplicate_customer_rows(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        group_by: str,
        rows: list[DuplicateDatasetRowInput],
    ) -> None:
        deduped_rows = _dedupe_duplicate_dataset_rows(rows)
        self._session.query(SystemDataOperationDatasetRowModel).filter(
            SystemDataOperationDatasetRowModel.run_id == run_id,
            SystemDataOperationDatasetRowModel.organization_id == organization_id,
        ).delete(synchronize_session=False)
        self._session.flush()

        now = datetime.now(tz=UTC)
        for offset in range(0, len(deduped_rows), BULK_INSERT_BATCH_SIZE):
            batch = deduped_rows[offset : offset + BULK_INSERT_BATCH_SIZE]
            self._session.bulk_save_objects(
                [
                    SystemDataOperationDatasetRowModel(
                        id=uuid4(),
                        run_id=run_id,
                        organization_id=organization_id,
                        entity_kind="customer",
                        entity_id=row.customer_id,
                        duplicate_group_key=row.group_key,
                        group_by=group_by,
                        match_score=None,
                        duplicate_reason=None,
                        fair_count=row.fair_count,
                        first_fair_name=row.first_fair_name,
                        created_at=now,
                    )
                    for row in batch
                ]
            )
        self._session.flush()

    def _duplicate_customer_query(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
    ) -> Query:
        query = (
            self._session.query(SystemDataOperationDatasetRowModel, CustomerModel)
            .join(
                CustomerModel,
                and_(
                    CustomerModel.id == SystemDataOperationDatasetRowModel.entity_id,
                    CustomerModel.organization_id == organization_id,
                ),
            )
            .filter(
                SystemDataOperationDatasetRowModel.run_id == run_id,
                SystemDataOperationDatasetRowModel.organization_id == organization_id,
                SystemDataOperationDatasetRowModel.entity_kind == "customer",
            )
        )
        query = exclude_merge_deleted_customers(query)
        if status is not None:
            query = query.filter(CustomerModel.status == status.value)
        if customer_type is not None:
            query = query.filter(CustomerModel.customer_type == customer_type.value)
        if country:
            query = query.filter(CustomerModel.country.ilike(country.strip()))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    *[field.ilike(pattern) for field in DATASET_DUPLICATE_SEARCH_FIELDS],
                    phone_search_exists(pattern),
                    email_search_exists(pattern),
                    website_search_exists(pattern),
                )
            )
        return query

    def list_duplicate_customers(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "duplicate_group_key",
        sort_dir: str = "asc",
    ) -> DatasetDuplicateCustomerListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._duplicate_customer_query(
            run_id=run_id,
            organization_id=organization_id,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
        )
        total = query.count()
        sort_column = DATASET_DUPLICATE_SORT_FIELDS.get(
            sort_by, SystemDataOperationDatasetRowModel.duplicate_group_key
        )
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=CustomerModel.id,
            nulls_last=sort_by
            in (
                "display_name",
                "company_name",
                "name",
                "legal_name",
                "trade_name",
                "match_score",
                "first_fair_name",
                "first_fair",
            ),
        )
        rows = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        total_pages = (total + page_params.page_size - 1) // page_params.page_size if total else 0
        return DatasetDuplicateCustomerListResult(
            items=[
                DatasetDuplicateCustomerItem(
                    customer=model_to_entity(customer_model),
                    group_key=dataset_row.duplicate_group_key or "",
                    group_by=dataset_row.group_by,
                    fair_count=dataset_row.fair_count or 0,
                    first_fair_name=dataset_row.first_fair_name,
                )
                for dataset_row, customer_model in rows
            ],
            page=page_params.page,
            page_size=page_params.page_size,
            total=total,
            total_pages=total_pages,
        )

    def list_all_duplicate_customers(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        sort_by: str = "duplicate_group_key",
        sort_dir: str = "asc",
    ) -> list[DatasetDuplicateCustomerItem]:
        query = self._duplicate_customer_query(
            run_id=run_id,
            organization_id=organization_id,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
        )
        sort_column = DATASET_DUPLICATE_SORT_FIELDS.get(
            sort_by, SystemDataOperationDatasetRowModel.duplicate_group_key
        )
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=CustomerModel.id,
            nulls_last=sort_by
            in (
                "display_name",
                "company_name",
                "name",
                "legal_name",
                "trade_name",
                "match_score",
                "first_fair_name",
                "first_fair",
            ),
        )
        rows = query.order_by(*order).all()
        return [
            DatasetDuplicateCustomerItem(
                customer=model_to_entity(customer_model),
                group_key=dataset_row.duplicate_group_key or "",
                group_by=dataset_row.group_by,
                fair_count=dataset_row.fair_count or 0,
                first_fair_name=dataset_row.first_fair_name,
            )
            for dataset_row, customer_model in rows
        ]

    def _customer_query(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
    ) -> Query:
        query = (
            self._session.query(CustomerModel)
            .join(
                SystemDataOperationDatasetRowModel,
                and_(
                    SystemDataOperationDatasetRowModel.entity_id == CustomerModel.id,
                    SystemDataOperationDatasetRowModel.run_id == run_id,
                    SystemDataOperationDatasetRowModel.organization_id == organization_id,
                    SystemDataOperationDatasetRowModel.entity_kind == "customer",
                ),
            )
            .filter(CustomerModel.organization_id == organization_id)
        )
        if status is not None:
            query = query.filter(CustomerModel.status == status.value)
        if customer_type is not None:
            query = query.filter(CustomerModel.customer_type == customer_type.value)
        if country:
            query = query.filter(CustomerModel.country.ilike(country.strip()))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    *[field.ilike(pattern) for field in DATASET_CUSTOMER_SEARCH_FIELDS],
                    phone_search_exists(pattern),
                    email_search_exists(pattern),
                    website_search_exists(pattern),
                )
            )
        return query

    def list_customers(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> DatasetCustomerListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._customer_query(
            run_id=run_id,
            organization_id=organization_id,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
        )
        total = query.count()
        sort_column = DATASET_CUSTOMER_SORT_FIELDS.get(sort_by, func.lower(CustomerModel.display_name))
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=CustomerModel.id,
            nulls_last=sort_by
            in ("display_name", "company_name", "name", "legal_name", "trade_name"),
        )
        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        total_pages = (total + page_params.page_size - 1) // page_params.page_size if total else 0
        return DatasetCustomerListResult(
            items=[model_to_entity(model) for model in models],
            page=page_params.page,
            page_size=page_params.page_size,
            total=total,
            total_pages=total_pages,
        )

    def list_all_customers(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> list[Customer]:
        query = self._customer_query(
            run_id=run_id,
            organization_id=organization_id,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
        )
        sort_column = DATASET_CUSTOMER_SORT_FIELDS.get(sort_by, func.lower(CustomerModel.display_name))
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=CustomerModel.id,
            nulls_last=sort_by
            in ("display_name", "company_name", "name", "legal_name", "trade_name"),
        )
        models = query.order_by(*order).all()
        return [model_to_entity(model) for model in models]

    def count_customer_rows(self, *, run_id: UUID, organization_id: UUID) -> int:
        return (
            self._session.query(SystemDataOperationDatasetRowModel)
            .filter(
                SystemDataOperationDatasetRowModel.run_id == run_id,
                SystemDataOperationDatasetRowModel.organization_id == organization_id,
                SystemDataOperationDatasetRowModel.entity_kind == "customer",
            )
            .count()
        )

    def customer_ids_in_dataset(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        customer_ids: list[UUID],
    ) -> set[UUID]:
        if not customer_ids:
            return set()
        rows = (
            self._session.query(SystemDataOperationDatasetRowModel.entity_id)
            .filter(
                SystemDataOperationDatasetRowModel.run_id == run_id,
                SystemDataOperationDatasetRowModel.organization_id == organization_id,
                SystemDataOperationDatasetRowModel.entity_kind == "customer",
                SystemDataOperationDatasetRowModel.entity_id.in_(customer_ids),
            )
            .all()
        )
        return {row[0] for row in rows}

    def remove_customer_rows(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        customer_ids: list[UUID],
    ) -> int:
        if not customer_ids:
            return 0
        deleted = (
            self._session.query(SystemDataOperationDatasetRowModel)
            .filter(
                SystemDataOperationDatasetRowModel.run_id == run_id,
                SystemDataOperationDatasetRowModel.organization_id == organization_id,
                SystemDataOperationDatasetRowModel.entity_kind == "customer",
                SystemDataOperationDatasetRowModel.entity_id.in_(customer_ids),
            )
            .delete(synchronize_session=False)
        )
        self._session.flush()
        return deleted

    def _duplicate_dataset_member_rows(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        duplicate_group_key: str | None = None,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
    ) -> list[tuple[SystemDataOperationDatasetRowModel, CustomerModel]]:
        query = (
            self._session.query(SystemDataOperationDatasetRowModel, CustomerModel)
            .join(
                CustomerModel,
                and_(
                    CustomerModel.id == SystemDataOperationDatasetRowModel.entity_id,
                    CustomerModel.organization_id == organization_id,
                ),
            )
            .filter(
                SystemDataOperationDatasetRowModel.run_id == run_id,
                SystemDataOperationDatasetRowModel.organization_id == organization_id,
                SystemDataOperationDatasetRowModel.entity_kind == "customer",
                SystemDataOperationDatasetRowModel.duplicate_group_key.isnot(None),
            )
        )
        query = exclude_merge_deleted_customers(query)
        if duplicate_group_key is not None:
            query = query.filter(
                SystemDataOperationDatasetRowModel.duplicate_group_key == duplicate_group_key
            )
        if status is not None:
            query = query.filter(CustomerModel.status == status.value)
        if customer_type is not None:
            query = query.filter(CustomerModel.customer_type == customer_type.value)
        if country:
            query = query.filter(CustomerModel.country.ilike(country.strip()))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    *[field.ilike(pattern) for field in DATASET_DUPLICATE_SEARCH_FIELDS],
                    phone_search_exists(pattern),
                    email_search_exists(pattern),
                    website_search_exists(pattern),
                )
            )
        return query.order_by(
            SystemDataOperationDatasetRowModel.duplicate_group_key.asc(),
            CustomerModel.display_name.asc(),
            CustomerModel.id.asc(),
        ).all()

    def _load_live_participations_by_customer(
        self,
        *,
        organization_id: UUID,
        customer_ids: list[UUID],
    ) -> dict[UUID, list[DuplicateGroupParticipationDetail]]:
        if not customer_ids:
            return {}
        rows = (
            self._session.query(CustomerFairParticipationModel, FairModel)
            .join(FairModel, FairModel.id == CustomerFairParticipationModel.fair_id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.customer_id.in_(customer_ids),
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .order_by(FairModel.name.asc(), CustomerFairParticipationModel.created_at.asc())
            .all()
        )
        by_customer: dict[UUID, list[DuplicateGroupParticipationDetail]] = defaultdict(list)
        for participation, fair in rows:
            fair_year = fair.start_date.year if fair.start_date else None
            by_customer[participation.customer_id].append(
                DuplicateGroupParticipationDetail(
                    fair_name=fair.name,
                    fair_year=fair_year,
                    hall=participation.hall,
                    stand=participation.stand,
                )
            )
        return dict(by_customer)

    def _build_duplicate_group_summaries(
        self,
        member_rows: list[tuple[SystemDataOperationDatasetRowModel, CustomerModel]],
        *,
        organization_id: UUID,
    ) -> list[DatasetDuplicateGroupSummary]:
        grouped: dict[str, dict[UUID, CustomerModel]] = defaultdict(dict)
        for dataset_row, customer_model in member_rows:
            group_key = dataset_row.duplicate_group_key
            if group_key:
                grouped[group_key][customer_model.id] = customer_model

        customer_ids = list(
            {
                customer_model.id
                for members_by_id in grouped.values()
                for customer_model in members_by_id.values()
            }
        )
        participations_by_customer = self._load_live_participations_by_customer(
            organization_id=organization_id,
            customer_ids=customer_ids,
        )

        summaries: list[DatasetDuplicateGroupSummary] = []
        for group_key, members_by_id in grouped.items():
            members = list(members_by_id.values())
            if len(members) < 2:
                continue
            group_by = next(
                (
                    dataset_row.group_by
                    for dataset_row, customer_model in member_rows
                    if dataset_row.duplicate_group_key == group_key
                    and dataset_row.group_by
                ),
                "company_name",
            )
            member_snapshots = [
                GroupMemberSnapshot(
                    customer_id=customer_model.id,
                    company_name=customer_model.display_name,
                    created_at=customer_model.created_at,
                )
                for customer_model in members
            ]
            participation_counts = {
                customer_model.id: len(participations_by_customer.get(customer_model.id, []))
                for customer_model in members
            }
            winner_id = pick_suggested_winner_customer(member_snapshots, participation_counts)
            winner_name = next(
                customer_model.display_name
                for customer_model in members
                if customer_model.id == winner_id
            )
            fair_names_set: dict[str, None] = {}
            created_times: list[datetime] = []
            for customer_model in members:
                created_times.append(customer_model.created_at)
                for participation in participations_by_customer.get(customer_model.id, []):
                    fair_names_set[participation.fair_name] = None
            fair_names = sorted(fair_names_set.keys())
            customer_names = sorted({customer_model.display_name for customer_model in members})
            summaries.append(
                DatasetDuplicateGroupSummary(
                    group_key=group_key,
                    group_by=group_by,
                    customer_count=len(members),
                    fair_count=len(fair_names),
                    fair_names=fair_names,
                    suggested_winner_customer_id=winner_id,
                    suggested_winner_company_name=winner_name,
                    created_at_min=min(created_times),
                    created_at_max=max(created_times),
                    customer_names=customer_names,
                )
            )
        return summaries

    def list_duplicate_groups(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "duplicate_group_key",
        sort_dir: str = "asc",
    ) -> DatasetDuplicateGroupListResult:
        member_rows = self._duplicate_dataset_member_rows(
            run_id=run_id,
            organization_id=organization_id,
        )
        summaries = self._build_duplicate_group_summaries(member_rows, organization_id=organization_id)

        if search and search.strip():
            pattern = search.strip().casefold()
            summaries = [
                summary
                for summary in summaries
                if pattern in summary.group_key.casefold()
                or pattern in summary.suggested_winner_company_name.casefold()
                or any(pattern in name.casefold() for name in summary.customer_names)
                or any(pattern in fair_name.casefold() for fair_name in summary.fair_names)
            ]

        reverse = sort_dir == "desc"
        run_group_by = member_rows[0][0].group_by if member_rows else None

        def sort_value(summary: DatasetDuplicateGroupSummary):
            if sort_by in ("group_key", "duplicate_group_key", "duplicate_group"):
                return summary.group_key.casefold()
            if sort_by == "group_by":
                return summary.group_by
            if sort_by == "customer_count":
                return summary.customer_count
            if sort_by == "fair_count":
                return summary.fair_count
            if sort_by in ("created_at_min", "created_at"):
                return summary.created_at_min.timestamp()
            if sort_by == "created_at_max":
                return summary.created_at_max.timestamp()
            if sort_by in ("suggested_winner_company_name", "suggested_winner"):
                return summary.suggested_winner_company_name.casefold()
            return summary.group_key.casefold()

        summaries.sort(key=sort_value, reverse=reverse)

        page_params = normalize_page_params(page, page_size)
        total = len(summaries)
        total_pages = (total + page_params.page_size - 1) // page_params.page_size if total else 0
        start = page_params.offset
        end = start + page_params.page_size
        live_customers = sum(summary.customer_count for summary in summaries)
        return DatasetDuplicateGroupListResult(
            items=summaries[start:end],
            page=page_params.page,
            page_size=page_params.page_size,
            total=total,
            total_pages=total_pages,
            group_by=run_group_by,
            live_duplicate_groups=total,
            live_customers_in_duplicate_groups=live_customers,
        )

    def get_duplicate_group_detail(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        group_key: str,
    ) -> DatasetDuplicateGroupDetail | None:
        member_rows = self._duplicate_dataset_member_rows(
            run_id=run_id,
            organization_id=organization_id,
            duplicate_group_key=group_key,
        )
        if not member_rows:
            return None

        unique_customer_ids = {customer_model.id for _, customer_model in member_rows}
        if len(unique_customer_ids) < 2:
            return None

        group_by = next(
            (dataset_row.group_by for dataset_row, _ in member_rows if dataset_row.group_by),
            "company_name",
        )
        customer_ids = [customer_model.id for _, customer_model in member_rows]
        participations_by_customer = self._load_live_participations_by_customer(
            organization_id=organization_id,
            customer_ids=customer_ids,
        )
        seen_customer_ids: set[UUID] = set()
        customers: list[DuplicateGroupCustomerDetail] = []
        for _, customer_model in member_rows:
            if customer_model.id in seen_customer_ids:
                continue
            seen_customer_ids.add(customer_model.id)
            customers.append(
                DuplicateGroupCustomerDetail(
                    customer=model_to_entity(customer_model),
                    participations=participations_by_customer.get(customer_model.id, []),
                )
            )
        return DatasetDuplicateGroupDetail(
            group_key=group_key,
            group_by=group_by,
            customers=customers,
        )
