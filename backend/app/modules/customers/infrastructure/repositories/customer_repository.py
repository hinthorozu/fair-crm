from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.core.pagination import PageParams, build_paginated_meta
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerListResult
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel

SEARCH_FIELDS = (
    CustomerModel.display_name,
    CustomerModel.normalized_name,
    CustomerModel.legal_name,
    CustomerModel.trade_name,
    CustomerModel.country,
    CustomerModel.city,
    CustomerModel.district,
    CustomerModel.address,
    CustomerModel.website,
    CustomerModel.phone,
    CustomerModel.email,
)

CUSTOMER_SORT_FIELDS = {
    "created_at": CustomerModel.created_at,
    "updated_at": CustomerModel.updated_at,
    "display_name": CustomerModel.display_name,
}


class SqlAlchemyCustomerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, customer: Customer) -> Customer:
        model = entity_to_model(customer)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def get_by_id(self, organization_id: UUID, customer_id: UUID) -> Customer | None:
        model = (
            self._session.query(CustomerModel)
            .filter(
                CustomerModel.organization_id == organization_id,
                CustomerModel.id == customer_id,
                CustomerModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def get_by_id_including_archived(
        self, organization_id: UUID, customer_id: UUID
    ) -> Customer | None:
        model = (
            self._session.query(CustomerModel)
            .filter(
                CustomerModel.organization_id == organization_id,
                CustomerModel.id == customer_id,
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def update(self, customer: Customer) -> Customer:
        model = (
            self._session.query(CustomerModel)
            .filter(
                CustomerModel.organization_id == customer.organization_id,
                CustomerModel.id == customer.id,
            )
            .one()
        )
        update_model_from_entity(model, customer)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def _filtered_query(
        self,
        organization_id: UUID,
        *,
        status: CustomerStatus | None = None,
        include_archived: bool = False,
        customer_type: CustomerType | None = None,
        search: str | None = None,
    ) -> Query:
        query = self._session.query(CustomerModel).filter(
            CustomerModel.organization_id == organization_id,
        )

        if status == CustomerStatus.ARCHIVED:
            query = query.filter(CustomerModel.deleted_at.isnot(None))
        elif status is not None:
            query = query.filter(CustomerModel.deleted_at.is_(None))
            query = query.filter(CustomerModel.status == status.value)
        elif include_archived:
            query = query.filter(CustomerModel.deleted_at.isnot(None))
        # else: no status filter → return all customers (active + archived)

        if customer_type is not None:
            query = query.filter(CustomerModel.customer_type == customer_type.value)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(*[field.ilike(pattern) for field in SEARCH_FIELDS]))

        return query

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        status: CustomerStatus | None = None,
        include_archived: bool = False,
        customer_type: CustomerType | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> CustomerListResult:
        page_params = PageParams(page=page, page_size=page_size)
        query = self._filtered_query(
            organization_id,
            status=status,
            include_archived=include_archived,
            customer_type=customer_type,
            search=search,
        )

        total = query.count()
        sort_column = CUSTOMER_SORT_FIELDS.get(sort_by, CustomerModel.created_at)
        if sort_dir == "asc":
            order = (sort_column.asc(), CustomerModel.id.asc())
        else:
            order = (sort_column.desc(), CustomerModel.id.desc())

        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )

        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return CustomerListResult(
            items=[model_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def list_all_active(self, organization_id: UUID) -> list[Customer]:
        models = (
            self._session.query(CustomerModel)
            .filter(
                CustomerModel.organization_id == organization_id,
                CustomerModel.deleted_at.is_(None),
            )
            .all()
        )
        return [model_to_entity(model) for model in models]

    def find_by_normalized_name(
        self,
        organization_id: UUID,
        normalized_name: str,
        *,
        exclude_id: UUID | None = None,
    ) -> list[Customer]:
        query = self._session.query(CustomerModel).filter(
            CustomerModel.organization_id == organization_id,
            CustomerModel.normalized_name == normalized_name,
            CustomerModel.deleted_at.is_(None),
        )
        if exclude_id is not None:
            query = query.filter(CustomerModel.id != exclude_id)
        return [model_to_entity(model) for model in query.all()]
