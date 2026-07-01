from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pagination import build_paginated_meta, normalize_page_params
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

PARTICIPATION_SORT_FIELDS = {
    "created_at": CustomerFairParticipationModel.created_at,
    "updated_at": CustomerFairParticipationModel.updated_at,
    "visited_at": CustomerFairParticipationModel.visited_at,
}


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

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
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
        total = query.count()
        sort_column = PARTICIPATION_SORT_FIELDS.get(sort_by, CustomerFairParticipationModel.created_at)
        if sort_dir.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        rows = query.offset(page_params.offset).limit(page_params.page_size).all()
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
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> FairParticipantListResult:
        page_params = normalize_page_params(page, page_size)
        query = (
            self._session.query(CustomerFairParticipationModel, CustomerModel)
            .join(CustomerModel, CustomerFairParticipationModel.customer_id == CustomerModel.id)
            .filter(
                CustomerFairParticipationModel.organization_id == organization_id,
                CustomerFairParticipationModel.fair_id == fair_id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
        )
        total = query.count()
        sort_column = PARTICIPATION_SORT_FIELDS.get(sort_by, CustomerFairParticipationModel.created_at)
        if sort_dir.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        rows = query.offset(page_params.offset).limit(page_params.page_size).all()
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
