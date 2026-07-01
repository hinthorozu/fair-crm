from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.domain.ports import ContactListResult
from app.modules.contacts.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.contacts.infrastructure.persistence.models import ContactModel

CONTACT_SORT_FIELDS = {
    "created_at": ContactModel.created_at,
    "updated_at": ContactModel.updated_at,
    "last_name": ContactModel.last_name,
    "first_name": ContactModel.first_name,
    "email": ContactModel.email,
    "department": ContactModel.department,
    "title": ContactModel.title,
}

SEARCH_FIELDS = (
    ContactModel.first_name,
    ContactModel.last_name,
    ContactModel.email,
    ContactModel.phone,
    ContactModel.mobile_phone,
    ContactModel.department,
    ContactModel.title,
)


class SqlAlchemyContactRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, contact: Contact) -> Contact:
        model = entity_to_model(contact)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def get_by_id(self, organization_id: UUID, contact_id: UUID) -> Contact | None:
        model = (
            self._session.query(ContactModel)
            .filter(
                ContactModel.organization_id == organization_id,
                ContactModel.id == contact_id,
                ContactModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def update(self, contact: Contact) -> Contact:
        model = (
            self._session.query(ContactModel)
            .filter(
                ContactModel.organization_id == contact.organization_id,
                ContactModel.id == contact.id,
            )
            .one()
        )
        update_model_from_entity(model, contact)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "first_name",
        sort_dir: str = "asc",
        include_deleted: bool = False,
    ) -> ContactListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(ContactModel).filter(
            ContactModel.organization_id == organization_id,
            ContactModel.customer_id == customer_id,
        )
        if not include_deleted:
            query = query.filter(ContactModel.deleted_at.is_(None))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(*[field.ilike(pattern) for field in SEARCH_FIELDS]))

        total = query.count()
        sort_column = CONTACT_SORT_FIELDS.get(sort_by, ContactModel.first_name)
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=ContactModel.id,
        )

        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return ContactListResult(
            items=[model_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def find_by_customer_and_name(
        self,
        organization_id: UUID,
        customer_id: UUID,
        first_name_lower: str,
        last_name_lower: str,
    ) -> Contact | None:
        models = (
            self._session.query(ContactModel)
            .filter(
                ContactModel.organization_id == organization_id,
                ContactModel.customer_id == customer_id,
                ContactModel.deleted_at.is_(None),
            )
            .all()
        )
        for model in models:
            if (
                model.first_name.strip().lower() == first_name_lower
                and model.last_name.strip().lower() == last_name_lower
            ):
                return model_to_entity(model)
        return None

    def clear_primary_for_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        exclude_contact_id: UUID | None = None,
    ) -> None:
        query = self._session.query(ContactModel).filter(
            ContactModel.organization_id == organization_id,
            ContactModel.customer_id == customer_id,
            ContactModel.is_primary.is_(True),
            ContactModel.deleted_at.is_(None),
        )
        if exclude_contact_id is not None:
            query = query.filter(ContactModel.id != exclude_contact_id)
        for model in query.all():
            model.is_primary = False
