from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.operations.domain.entities import OperationRunItem
from app.modules.operations.domain.ports import OperationRunItemListResult
from app.modules.operations.infrastructure.persistence.mappers import (
    run_item_to_entity,
    run_item_to_model,
    update_run_item_model,
)
from app.modules.operations.infrastructure.persistence.models import OperationRunItemModel

ITEM_SORT_FIELDS = {
    "created_at": OperationRunItemModel.created_at,
    "updated_at": OperationRunItemModel.updated_at,
    "status": OperationRunItemModel.status,
    "attempt": OperationRunItemModel.attempt,
}


class SqlAlchemyOperationRunItemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: OperationRunItem) -> OperationRunItem:
        model = run_item_to_model(item)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return run_item_to_entity(model)

    def add_many(self, items: list[OperationRunItem]) -> list[OperationRunItem]:
        models = [run_item_to_model(item) for item in items]
        self._session.add_all(models)
        self._session.flush()
        for model in models:
            self._session.refresh(model)
        return [run_item_to_entity(model) for model in models]

    def get_by_id(self, organization_id: UUID, item_id: UUID) -> OperationRunItem | None:
        model = (
            self._session.query(OperationRunItemModel)
            .filter(
                OperationRunItemModel.organization_id == organization_id,
                OperationRunItemModel.id == item_id,
            )
            .one_or_none()
        )
        return run_item_to_entity(model) if model else None

    def update(self, item: OperationRunItem) -> OperationRunItem:
        model = (
            self._session.query(OperationRunItemModel)
            .filter(
                OperationRunItemModel.organization_id == item.organization_id,
                OperationRunItemModel.id == item.id,
            )
            .one()
        )
        update_run_item_model(model, item)
        self._session.flush()
        self._session.refresh(model)
        return run_item_to_entity(model)

    def list_by_run(
        self,
        organization_id: UUID,
        run_id: UUID,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "asc",
    ) -> OperationRunItemListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(OperationRunItemModel).filter(
            OperationRunItemModel.organization_id == organization_id,
            OperationRunItemModel.run_id == run_id,
        )
        if status:
            query = query.filter(OperationRunItemModel.status == status)
        total = query.count()
        sort_column = ITEM_SORT_FIELDS.get(sort_by, OperationRunItemModel.created_at)
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=OperationRunItemModel.id,
        )
        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return OperationRunItemListResult(
            items=[run_item_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )
