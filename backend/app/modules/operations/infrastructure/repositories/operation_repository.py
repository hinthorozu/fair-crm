from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.operations.domain.entities import Operation
from app.modules.operations.domain.ports import OperationListResult
from app.modules.operations.infrastructure.persistence.mappers import (
    operation_to_entity,
    operation_to_model,
    update_operation_model,
)
from app.modules.operations.infrastructure.persistence.models import OperationModel

OPERATION_SORT_FIELDS = {
    "title": OperationModel.title,
    "created_at": OperationModel.created_at,
    "updated_at": OperationModel.updated_at,
    "status": OperationModel.status,
    "operation_type": OperationModel.operation_type,
    "priority": OperationModel.priority,
}


class SqlAlchemyOperationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, operation: Operation) -> Operation:
        model = operation_to_model(operation)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return operation_to_entity(model)

    def get_by_id(self, organization_id: UUID, operation_id: UUID) -> Operation | None:
        model = (
            self._session.query(OperationModel)
            .filter(
                OperationModel.organization_id == organization_id,
                OperationModel.id == operation_id,
            )
            .one_or_none()
        )
        return operation_to_entity(model) if model else None

    def update(self, operation: Operation) -> Operation:
        model = (
            self._session.query(OperationModel)
            .filter(
                OperationModel.organization_id == operation.organization_id,
                OperationModel.id == operation.id,
            )
            .one()
        )
        update_operation_model(model, operation)
        self._session.flush()
        self._session.refresh(model)
        return operation_to_entity(model)

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        operation_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> OperationListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(OperationModel).filter(
            OperationModel.organization_id == organization_id
        )
        if operation_type:
            query = query.filter(OperationModel.operation_type == operation_type)
        if status:
            query = query.filter(OperationModel.status == status)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    OperationModel.title.ilike(term),
                    OperationModel.description.ilike(term),
                )
            )

        total = query.count()
        sort_column = OPERATION_SORT_FIELDS.get(sort_by, OperationModel.created_at)
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "desc",
            tie_breaker=OperationModel.id,
        )
        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return OperationListResult(
            items=[operation_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )
