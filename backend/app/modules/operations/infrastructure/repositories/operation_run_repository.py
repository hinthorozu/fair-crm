from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.operations.domain.entities import OperationRun
from app.modules.operations.domain.ports import OperationRunListResult
from app.modules.operations.infrastructure.persistence.mappers import (
    run_to_entity,
    run_to_model,
    update_run_model,
)
from app.modules.operations.infrastructure.persistence.models import OperationRunModel

RUN_SORT_FIELDS = {
    "created_at": OperationRunModel.created_at,
    "updated_at": OperationRunModel.updated_at,
    "started_at": OperationRunModel.started_at,
    "finished_at": OperationRunModel.finished_at,
    "status": OperationRunModel.status,
    "attempt": OperationRunModel.attempt,
}


class SqlAlchemyOperationRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, run: OperationRun) -> OperationRun:
        model = run_to_model(run)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return run_to_entity(model)

    def get_by_id(self, organization_id: UUID, run_id: UUID) -> OperationRun | None:
        model = (
            self._session.query(OperationRunModel)
            .filter(
                OperationRunModel.organization_id == organization_id,
                OperationRunModel.id == run_id,
            )
            .one_or_none()
        )
        return run_to_entity(model) if model else None

    def update(self, run: OperationRun) -> OperationRun:
        model = (
            self._session.query(OperationRunModel)
            .filter(
                OperationRunModel.organization_id == run.organization_id,
                OperationRunModel.id == run.id,
            )
            .one()
        )
        update_run_model(model, run)
        self._session.flush()
        self._session.refresh(model)
        return run_to_entity(model)

    def list_by_operation(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> OperationRunListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(OperationRunModel).filter(
            OperationRunModel.organization_id == organization_id,
            OperationRunModel.operation_id == operation_id,
        )
        total = query.count()
        sort_column = RUN_SORT_FIELDS.get(sort_by, OperationRunModel.created_at)
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "desc",
            tie_breaker=OperationRunModel.id,
        )
        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return OperationRunListResult(
            items=[run_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )
