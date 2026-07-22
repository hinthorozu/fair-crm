from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.customers.infrastructure.persistence.communication_query_helpers import (
    email_search_exists,
    phone_search_exists,
    primary_email_subquery,
    primary_phone_subquery,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.ports import (
    CustomerParticipationListResult,
    CustomerParticipationRow,
    FairParticipantListResult,
    FairParticipantRow,
)
from app.modules.participations.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel

PARTICIPATION_BASE_SORT_FIELDS = {
    "created_at": CustomerFairParticipationModel.created_at,
    "updated_at": CustomerFairParticipationModel.updated_at,
    "hall": CustomerFairParticipationModel.hall,
    "stand": CustomerFairParticipationModel.stand,
    "notes": CustomerFairParticipationModel.notes,
}

CUSTOMER_LIST_SORT_FIELDS = {
    **PARTICIPATION_BASE_SORT_FIELDS,
    "fair_start_date": FairModel.start_date,
    "fair_name": FairModel.name,
}

FAIR_LIST_SORT_FIELDS = {
    **PARTICIPATION_BASE_SORT_FIELDS,
    "company_name": CustomerModel.display_name,
    "email": primary_email_subquery(),
    "phone": primary_phone_subquery(),
    "country": CustomerModel.country,
    "city": CustomerModel.city,
}

FAIR_PARTICIPANT_SEARCH_FIELDS = (
    CustomerModel.display_name,
    CustomerModel.country,
    CustomerModel.city,
    CustomerFairParticipationModel.hall,
    CustomerFairParticipationModel.stand,
)

CUSTOMER_PARTICIPATION_SEARCH_FIELDS = (
    FairModel.name,
    CustomerFairParticipationModel.hall,
    CustomerFairParticipationModel.stand,
)


class SqlAlchemyParticipationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, participation: CustomerFairParticipation) -> CustomerFairParticipation:
        model = entity_to_model(participation)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def get_by_id(
        self, organization_id: UUID, participation_id: UUID
    ) -> CustomerFairParticipation | None:
        model = (
            self._session.query(CustomerFairParticipationModel)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.id == participation_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def update(self, participation: CustomerFairParticipation) -> CustomerFairParticipation:
        model = (
            self._session.query(CustomerFairParticipationModel)
            .filter(
                CustomerFairParticipationModel.organization_id == participation.organization_id,
                CustomerFairParticipationModel.id == participation.id,
            )
            .one()
        )
        update_model_from_entity(model, participation)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def exists_active(self, organization_id: UUID, customer_id: UUID, fair_id: UUID) -> bool:
        return (
            self._session.query(CustomerFairParticipationModel.id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.customer_id == customer_id,
                CustomerFairParticipationModel.fair_id == fair_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .first()
            is not None
        )

    def get_active_by_customer_and_fair(
        self, organization_id: UUID, customer_id: UUID, fair_id: UUID
    ) -> CustomerFairParticipation | None:
        model = (
            self._session.query(CustomerFairParticipationModel)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.customer_id == customer_id,
                CustomerFairParticipationModel.fair_id == fair_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def map_active_customer_ids_for_fair(
        self, organization_id: UUID, fair_id: UUID
    ) -> dict[UUID, UUID]:
        rows = (
            self._session.query(
                CustomerFairParticipationModel.customer_id,
                CustomerFairParticipationModel.id,
            )
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id == fair_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .all()
        )
        return {customer_id: participation_id for customer_id, participation_id in rows}

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "fair_start_date",
        sort_dir: str = "desc",
    ) -> CustomerParticipationListResult:
        page_params = normalize_page_params(page, page_size)
        query = (
            self._session.query(CustomerFairParticipationModel, FairModel)
            .join(FairModel, CustomerFairParticipationModel.fair_id == FairModel.id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.customer_id == customer_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(*[field.ilike(pattern) for field in CUSTOMER_PARTICIPATION_SEARCH_FIELDS])
            )

        total = query.count()
        sort_column = CUSTOMER_LIST_SORT_FIELDS.get(sort_by, FairModel.start_date)
        nulls_last = sort_by == "fair_start_date"
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "desc",
            tie_breaker=CustomerFairParticipationModel.id,
            nulls_last=nulls_last,
        )
        rows = query.order_by(*order).offset(page_params.offset).limit(page_params.page_size).all()
        items = [
            CustomerParticipationRow(
                participation=model_to_entity(part_model),
                fair_name=fair_model.name,
                fair_start_date=fair_model.start_date,
                fair_end_date=fair_model.end_date,
            )
            for part_model, fair_model in rows
        ]
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return CustomerParticipationListResult(
            items=items,
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def list_by_fair(
        self,
        organization_id: UUID,
        fair_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "company_name",
        sort_dir: str = "asc",
    ) -> FairParticipantListResult:
        page_params = normalize_page_params(page, page_size)
        primary_phone = primary_phone_subquery()
        primary_email = primary_email_subquery()
        query = (
            self._session.query(
                CustomerFairParticipationModel,
                CustomerModel,
                primary_phone,
                primary_email,
            )
            .join(CustomerModel, CustomerFairParticipationModel.customer_id == CustomerModel.id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id == fair_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    *[field.ilike(pattern) for field in FAIR_PARTICIPANT_SEARCH_FIELDS],
                    phone_search_exists(pattern),
                    email_search_exists(pattern),
                )
            )

        total = query.count()
        sort_column = FAIR_LIST_SORT_FIELDS.get(sort_by, CustomerModel.display_name)
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=CustomerFairParticipationModel.id,
        )
        rows = query.order_by(*order).offset(page_params.offset).limit(page_params.page_size).all()
        items = [
            FairParticipantRow(
                participation=model_to_entity(part_model),
                company_name=customer_model.display_name,
                email=primary_email_value,
                phone=primary_phone_value,
                country=customer_model.country,
                city=customer_model.city,
            )
            for part_model, customer_model, primary_phone_value, primary_email_value in rows
        ]
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return FairParticipantListResult(
            items=items,
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

