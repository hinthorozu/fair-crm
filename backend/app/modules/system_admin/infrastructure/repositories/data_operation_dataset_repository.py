from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, asc, desc, func, or_
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
from app.modules.customers.application.duplicate_merge_classification import (
    classify_duplicate_match,
    humanize_duplicate_reason,
    summarize_group_match,
)
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
    match_score: int | None = None
    duplicate_reason: str | None = None


@dataclass(frozen=True)
class DatasetDuplicateCustomerItem:
    customer: Customer
    group_key: str
    group_by: str | None
    fair_count: int
    first_fair_name: str | None
    match_score: int | None = None
    duplicate_reason: str | None = None
    match_explanation: str | None = None
    merge_classification: str | None = None


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
    min_match_score: int | None = None
    max_match_score: int | None = None
    merge_classification: str | None = None
    review_tier: str | None = None
    requires_manual_review: bool = False
    match_explanation_summary: str | None = None


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
    match_score: int | None = None
    duplicate_reason: str | None = None
    match_explanation: str | None = None
    merge_classification: str | None = None


@dataclass(frozen=True)
class DatasetDuplicateGroupDetail:
    group_key: str
    group_by: str
    customers: list[DuplicateGroupCustomerDetail]
    min_match_score: int | None = None
    max_match_score: int | None = None
    merge_classification: str | None = None
    review_tier: str | None = None
    requires_manual_review: bool = False
    match_explanation_summary: str | None = None


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


def _duplicate_customer_item_from_row(
    dataset_row: SystemDataOperationDatasetRowModel,
    customer_model: CustomerModel,
) -> DatasetDuplicateCustomerItem:
    match_score = dataset_row.match_score
    duplicate_reason = dataset_row.duplicate_reason
    merge_classification = classify_duplicate_match(
        match_score=match_score,
        duplicate_reason=duplicate_reason,
    )
    return DatasetDuplicateCustomerItem(
        customer=model_to_entity(customer_model),
        group_key=dataset_row.duplicate_group_key or "",
        group_by=dataset_row.group_by,
        fair_count=dataset_row.fair_count or 0,
        first_fair_name=dataset_row.first_fair_name,
        match_score=match_score,
        duplicate_reason=duplicate_reason,
        match_explanation=humanize_duplicate_reason(duplicate_reason),
        merge_classification=merge_classification,
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
                        match_score=row.match_score,
                        duplicate_reason=row.duplicate_reason,
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
                _duplicate_customer_item_from_row(dataset_row, customer_model)
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
            _duplicate_customer_item_from_row(dataset_row, customer_model)
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
        duplicate_group_keys: list[str] | None = None,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
    ) -> list[tuple[SystemDataOperationDatasetRowModel, CustomerModel]]:
        query = self._duplicate_dataset_member_models_query(
            run_id=run_id,
            organization_id=organization_id,
            duplicate_group_key=duplicate_group_key,
            duplicate_group_keys=duplicate_group_keys,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
        )
        return query.order_by(
            SystemDataOperationDatasetRowModel.duplicate_group_key.asc(),
            CustomerModel.display_name.asc(),
            CustomerModel.id.asc(),
        ).all()

    def _duplicate_dataset_member_models_query(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        duplicate_group_key: str | None = None,
        duplicate_group_keys: list[str] | None = None,
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
                SystemDataOperationDatasetRowModel.duplicate_group_key.isnot(None),
            )
        )
        query = exclude_merge_deleted_customers(query)
        if duplicate_group_key is not None:
            query = query.filter(
                SystemDataOperationDatasetRowModel.duplicate_group_key == duplicate_group_key
            )
        if duplicate_group_keys is not None:
            query = query.filter(
                SystemDataOperationDatasetRowModel.duplicate_group_key.in_(duplicate_group_keys)
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
        return query

    def _duplicate_group_member_projection_query(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        duplicate_group_keys: list[str] | None = None,
        matching_group_keys=None,
    ):
        query = (
            self._session.query(
                SystemDataOperationDatasetRowModel.duplicate_group_key.label("group_key"),
                SystemDataOperationDatasetRowModel.group_by.label("group_by"),
                CustomerModel.id.label("customer_id"),
                CustomerModel.display_name.label("display_name"),
                CustomerModel.created_at.label("created_at"),
            )
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
                CustomerModel.status != CustomerStatus.DELETED.value,
            )
        )
        if duplicate_group_keys is not None:
            query = query.filter(
                SystemDataOperationDatasetRowModel.duplicate_group_key.in_(duplicate_group_keys)
            )
        if matching_group_keys is not None:
            query = query.filter(
                SystemDataOperationDatasetRowModel.duplicate_group_key.in_(matching_group_keys)
            )
        return query

    def _matching_duplicate_group_keys_select(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        search: str,
    ):
        pattern = f"%{search.strip()}%"
        base_filters = (
            SystemDataOperationDatasetRowModel.run_id == run_id,
            SystemDataOperationDatasetRowModel.organization_id == organization_id,
            SystemDataOperationDatasetRowModel.entity_kind == "customer",
            SystemDataOperationDatasetRowModel.duplicate_group_key.isnot(None),
            CustomerModel.status != CustomerStatus.DELETED.value,
        )
        member_keys = (
            self._session.query(SystemDataOperationDatasetRowModel.duplicate_group_key)
            .join(
                CustomerModel,
                and_(
                    CustomerModel.id == SystemDataOperationDatasetRowModel.entity_id,
                    CustomerModel.organization_id == organization_id,
                ),
            )
            .filter(
                *base_filters,
                or_(
                    SystemDataOperationDatasetRowModel.duplicate_group_key.ilike(pattern),
                    *[field.ilike(pattern) for field in DATASET_DUPLICATE_SEARCH_FIELDS],
                    phone_search_exists(pattern),
                    email_search_exists(pattern),
                    website_search_exists(pattern),
                ),
            )
        )
        fair_keys = (
            self._session.query(SystemDataOperationDatasetRowModel.duplicate_group_key)
            .join(
                CustomerModel,
                and_(
                    CustomerModel.id == SystemDataOperationDatasetRowModel.entity_id,
                    CustomerModel.organization_id == organization_id,
                ),
            )
            .join(
                CustomerFairParticipationModel,
                and_(
                    CustomerFairParticipationModel.customer_id == CustomerModel.id,
                    CustomerFairParticipationModel.organization_id == organization_id,
                    CustomerFairParticipationModel.deleted_at.is_(None),
                ),
            )
            .join(FairModel, FairModel.id == CustomerFairParticipationModel.fair_id)
            .filter(*base_filters, FairModel.name.ilike(pattern))
        )
        return member_keys.union(fair_keys)

    def _duplicate_group_fair_count_subquery(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
    ):
        return (
            self._session.query(
                SystemDataOperationDatasetRowModel.duplicate_group_key.label("group_key"),
                func.count(func.distinct(FairModel.id)).label("fair_count"),
            )
            .join(
                CustomerModel,
                and_(
                    CustomerModel.id == SystemDataOperationDatasetRowModel.entity_id,
                    CustomerModel.organization_id == organization_id,
                ),
            )
            .join(
                CustomerFairParticipationModel,
                and_(
                    CustomerFairParticipationModel.customer_id == CustomerModel.id,
                    CustomerFairParticipationModel.organization_id == organization_id,
                    CustomerFairParticipationModel.deleted_at.is_(None),
                ),
            )
            .join(FairModel, FairModel.id == CustomerFairParticipationModel.fair_id)
            .filter(
                SystemDataOperationDatasetRowModel.run_id == run_id,
                SystemDataOperationDatasetRowModel.organization_id == organization_id,
                SystemDataOperationDatasetRowModel.entity_kind == "customer",
                SystemDataOperationDatasetRowModel.duplicate_group_key.isnot(None),
                CustomerModel.status != CustomerStatus.DELETED.value,
            )
            .group_by(SystemDataOperationDatasetRowModel.duplicate_group_key)
            .subquery("duplicate_group_fair_counts")
        )

    def _duplicate_group_aggregates_query(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        search: str | None = None,
    ):
        matching_group_keys = None
        if search and search.strip():
            matching_group_keys = self._matching_duplicate_group_keys_select(
                run_id=run_id,
                organization_id=organization_id,
                search=search,
            )
        members = self._duplicate_group_member_projection_query(
            run_id=run_id,
            organization_id=organization_id,
            matching_group_keys=matching_group_keys,
        ).subquery("duplicate_group_members")
        aggregates = (
            self._session.query(
                members.c.group_key.label("group_key"),
                func.min(members.c.group_by).label("group_by"),
                func.count(func.distinct(members.c.customer_id)).label("customer_count"),
                func.min(members.c.created_at).label("created_at_min"),
                func.max(members.c.created_at).label("created_at_max"),
            )
            .group_by(members.c.group_key)
            .having(func.count(func.distinct(members.c.customer_id)) >= 2)
            .subquery("duplicate_group_aggregates")
        )
        fair_counts = self._duplicate_group_fair_count_subquery(
            run_id=run_id,
            organization_id=organization_id,
        )
        return self._session.query(
            aggregates.c.group_key,
            aggregates.c.group_by,
            aggregates.c.customer_count,
            aggregates.c.created_at_min,
            aggregates.c.created_at_max,
            func.coalesce(fair_counts.c.fair_count, 0).label("fair_count"),
        ).outerjoin(fair_counts, fair_counts.c.group_key == aggregates.c.group_key)

    def _load_participation_counts_by_customer(
        self,
        *,
        organization_id: UUID,
        customer_ids: list[UUID],
    ) -> dict[UUID, int]:
        if not customer_ids:
            return {}
        rows = (
            self._session.query(
                CustomerFairParticipationModel.customer_id,
                func.count(CustomerFairParticipationModel.id),
            )
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.customer_id.in_(customer_ids),
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .group_by(CustomerFairParticipationModel.customer_id)
            .all()
        )
        return {customer_id: count for customer_id, count in rows}

    def _compute_suggested_winner_by_group(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        group_keys: list[str] | None = None,
    ) -> dict[str, tuple[UUID, str]]:
        rows = self._duplicate_group_member_projection_query(
            run_id=run_id,
            organization_id=organization_id,
            duplicate_group_keys=group_keys,
        ).all()
        grouped: dict[str, list[GroupMemberSnapshot]] = defaultdict(list)
        customer_ids: list[UUID] = []
        for row in rows:
            grouped[row.group_key].append(
                GroupMemberSnapshot(
                    customer_id=row.customer_id,
                    company_name=row.display_name,
                    created_at=row.created_at,
                )
            )
            customer_ids.append(row.customer_id)
        participation_counts = self._load_participation_counts_by_customer(
            organization_id=organization_id,
            customer_ids=list(set(customer_ids)),
        )
        winners: dict[str, tuple[UUID, str]] = {}
        for group_key, snapshots in grouped.items():
            if len(snapshots) < 2:
                continue
            winner_id = pick_suggested_winner_customer(snapshots, participation_counts)
            winner_name = next(
                snapshot.company_name
                for snapshot in snapshots
                if snapshot.customer_id == winner_id
            )
            winners[group_key] = (winner_id, winner_name)
        return winners

    def _duplicate_group_aggregate_order(
        self,
        subquery,
        *,
        sort_by: str,
        sort_dir: str,
    ) -> tuple:
        reverse = sort_dir == "desc"
        tie_breaker = asc(subquery.c.group_key)
        sort_columns = {
            "group_key": subquery.c.group_key,
            "duplicate_group_key": subquery.c.group_key,
            "duplicate_group": subquery.c.group_key,
            "group_by": subquery.c.group_by,
            "customer_count": subquery.c.customer_count,
            "created_at_min": subquery.c.created_at_min,
            "created_at": subquery.c.created_at_min,
            "created_at_max": subquery.c.created_at_max,
            "fair_count": subquery.c.fair_count,
        }
        column = sort_columns.get(sort_by, subquery.c.group_key)
        primary = desc(column) if reverse else asc(column)
        return (primary, tie_breaker)

    def _summaries_for_group_keys(
        self,
        *,
        run_id: UUID,
        organization_id: UUID,
        group_keys: list[str],
    ) -> dict[str, DatasetDuplicateGroupSummary]:
        if not group_keys:
            return {}
        member_rows = self._duplicate_dataset_member_rows(
            run_id=run_id,
            organization_id=organization_id,
            duplicate_group_keys=group_keys,
        )
        summaries = self._build_duplicate_group_summaries(
            member_rows,
            organization_id=organization_id,
        )
        return {summary.group_key: summary for summary in summaries}

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
            group_dataset_rows = [
                dataset_row
                for dataset_row, customer_model in member_rows
                if dataset_row.duplicate_group_key == group_key
            ]
            group_match = summarize_group_match(
                match_scores=[row.match_score for row in group_dataset_rows],
                duplicate_reasons=[row.duplicate_reason for row in group_dataset_rows],
            )
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
                    min_match_score=group_match.min_match_score,
                    max_match_score=group_match.max_match_score,
                    merge_classification=group_match.merge_classification,
                    review_tier=group_match.review_tier,
                    requires_manual_review=group_match.requires_manual_review,
                    match_explanation_summary=group_match.match_explanation_summary,
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
        page_params = normalize_page_params(page, page_size)
        aggregates_subquery = self._duplicate_group_aggregates_query(
            run_id=run_id,
            organization_id=organization_id,
            search=search,
        ).subquery("duplicate_group_page_source")
        totals = self._session.query(
            func.count(),
            func.coalesce(func.sum(aggregates_subquery.c.customer_count), 0),
        ).one()
        total = int(totals[0] or 0)
        total_pages = (total + page_params.page_size - 1) // page_params.page_size if total else 0
        live_customers = int(totals[1] or 0)
        run_group_by = (
            self._session.query(SystemDataOperationDatasetRowModel.group_by)
            .filter(
                SystemDataOperationDatasetRowModel.run_id == run_id,
                SystemDataOperationDatasetRowModel.organization_id == organization_id,
                SystemDataOperationDatasetRowModel.group_by.isnot(None),
            )
            .limit(1)
            .scalar()
        )

        if sort_by in ("suggested_winner_company_name", "suggested_winner"):
            all_group_keys = [
                row.group_key
                for row in self._session.query(aggregates_subquery.c.group_key).all()
            ]
            winner_by_group = self._compute_suggested_winner_by_group(
                run_id=run_id,
                organization_id=organization_id,
                group_keys=all_group_keys,
            )
            aggregate_rows = self._session.query(aggregates_subquery).all()
            reverse = sort_dir == "desc"
            aggregate_rows.sort(
                key=lambda row: winner_by_group.get(row.group_key, ("", ""))[1].casefold(),
                reverse=reverse,
            )
            page_rows = aggregate_rows[page_params.offset : page_params.offset + page_params.page_size]
        else:
            page_rows = (
                self._session.query(aggregates_subquery)
                .order_by(
                    *self._duplicate_group_aggregate_order(
                        aggregates_subquery,
                        sort_by=sort_by,
                        sort_dir=sort_dir,
                    )
                )
                .offset(page_params.offset)
                .limit(page_params.page_size)
                .all()
            )

        page_group_keys = [row.group_key for row in page_rows]
        summaries_by_key = self._summaries_for_group_keys(
            run_id=run_id,
            organization_id=organization_id,
            group_keys=page_group_keys,
        )
        items = [summaries_by_key[group_key] for group_key in page_group_keys if group_key in summaries_by_key]

        return DatasetDuplicateGroupListResult(
            items=items,
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
        group_dataset_rows: list[SystemDataOperationDatasetRowModel] = []
        for dataset_row, customer_model in member_rows:
            group_dataset_rows.append(dataset_row)
            if customer_model.id in seen_customer_ids:
                continue
            seen_customer_ids.add(customer_model.id)
            merge_classification = classify_duplicate_match(
                match_score=dataset_row.match_score,
                duplicate_reason=dataset_row.duplicate_reason,
            )
            customers.append(
                DuplicateGroupCustomerDetail(
                    customer=model_to_entity(customer_model),
                    participations=participations_by_customer.get(customer_model.id, []),
                    match_score=dataset_row.match_score,
                    duplicate_reason=dataset_row.duplicate_reason,
                    match_explanation=humanize_duplicate_reason(dataset_row.duplicate_reason),
                    merge_classification=merge_classification,
                )
            )
        group_match = summarize_group_match(
            match_scores=[row.match_score for row in group_dataset_rows],
            duplicate_reasons=[row.duplicate_reason for row in group_dataset_rows],
        )
        return DatasetDuplicateGroupDetail(
            group_key=group_key,
            group_by=group_by,
            customers=customers,
            min_match_score=group_match.min_match_score,
            max_match_score=group_match.max_match_score,
            merge_classification=group_match.merge_classification,
            review_tier=group_match.review_tier,
            requires_manual_review=group_match.requires_manual_review,
            match_explanation_summary=group_match.match_explanation_summary,
        )
