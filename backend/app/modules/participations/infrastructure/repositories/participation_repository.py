from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.contacts.infrastructure.persistence.models import ContactModel
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
    "visited_at": CustomerFairParticipationModel.visited_at,
    "hall": CustomerFairParticipationModel.hall,
    "stand": CustomerFairParticipationModel.stand,
    "participation_status": CustomerFairParticipationModel.participation_status,
}

CUSTOMER_LIST_SORT_FIELDS = {
    **PARTICIPATION_BASE_SORT_FIELDS,
    "fair_start_date": FairModel.start_date,
    "fair_name": FairModel.name,
}

FAIR_LIST_SORT_FIELDS = {
    **PARTICIPATION_BASE_SORT_FIELDS,
    "company_name": CustomerModel.display_name,
    "email": CustomerModel.email,
    "phone": CustomerModel.phone,
    "country": CustomerModel.country,
    "city": CustomerModel.city,
}

FAIR_PARTICIPANT_SEARCH_FIELDS = (
    CustomerModel.display_name,
    CustomerModel.email,
    CustomerModel.phone,
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

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        search: str | None = None,
        participation_status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "fair_start_date",
        sort_dir: str = "desc",
    ) -> CustomerParticipationListResult:
        page_params = normalize_page_params(page, page_size)
        contact = aliased(ContactModel)
        query = (
            self._session.query(CustomerFairParticipationModel, FairModel)
            .join(FairModel, CustomerFairParticipationModel.fair_id == FairModel.id)
            .outerjoin(contact, CustomerFairParticipationModel.primary_contact_id == contact.id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.customer_id == customer_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
        )
        if participation_status:
            query = query.filter(
                CustomerFairParticipationModel.participation_status == participation_status.strip()
            )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(*[field.ilike(pattern) for field in CUSTOMER_PARTICIPATION_SEARCH_FIELDS])
            )

        total = query.count()
        sort_fields = {**CUSTOMER_LIST_SORT_FIELDS, "primary_contact_name": contact.last_name}
        sort_column = sort_fields.get(sort_by, FairModel.start_date)
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
        participation_status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "company_name",
        sort_dir: str = "asc",
    ) -> FairParticipantListResult:
        page_params = normalize_page_params(page, page_size)
        contact = aliased(ContactModel)
        query = (
            self._session.query(CustomerFairParticipationModel, CustomerModel)
            .join(CustomerModel, CustomerFairParticipationModel.customer_id == CustomerModel.id)
            .outerjoin(contact, CustomerFairParticipationModel.primary_contact_id == contact.id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id == fair_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
        )
        if participation_status:
            query = query.filter(
                CustomerFairParticipationModel.participation_status == participation_status.strip()
            )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(*[field.ilike(pattern) for field in FAIR_PARTICIPANT_SEARCH_FIELDS])
            )

        total = query.count()
        sort_fields = {**FAIR_LIST_SORT_FIELDS, "primary_contact_name": contact.last_name}
        sort_column = sort_fields.get(sort_by, CustomerModel.display_name)
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
                email=customer_model.email,
                phone=customer_model.phone,
                country=customer_model.country,
                city=customer_model.city,
            )
            for part_model, customer_model in rows
        ]
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return FairParticipantListResult(
            items=items,
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def get_contact_full_name(self, organization_id: UUID, contact_id: UUID | None) -> str | None:
        if contact_id is None:
            return None
        model = (
            self._session.query(ContactModel)
            .filter(
                ContactModel.organization_id == organization_id,
                ContactModel.id == contact_id,
                ContactModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if model is None:
            return None
        return f"{model.first_name} {model.last_name}".strip()
