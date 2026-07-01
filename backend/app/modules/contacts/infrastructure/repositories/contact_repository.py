from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pagination import PageParams, build_paginated_meta, normalize_page_params
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
}


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
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        include_deleted: bool = False,
    ) -> ContactListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(ContactModel).filter(
            ContactModel.organization_id == organization_id,
            ContactModel.customer_id == customer_id,
        )
        if not include_deleted:
            query = query.filter(ContactModel.deleted_at.is_(None))

        total = query.count()
        sort_column = CONTACT_SORT_FIELDS.get(sort_by, ContactModel.created_at)
        if sort_dir == "asc":
            order = (sort_column.asc(), ContactModel.id.asc())
        else:
            order = (sort_column.desc(), ContactModel.id.desc())

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
