from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.worklist_ports import OutcomeListResult
from app.modules.todos.infrastructure.persistence.worklist_mappers import (
    outcome_entity_to_model,
    outcome_model_to_entity,
    update_outcome_model_from_entity,
)
from app.modules.todos.infrastructure.persistence.models import TodoOutcomeDefinitionModel

OUTCOME_SORT_FIELDS = {
    "sort_order": TodoOutcomeDefinitionModel.sort_order,
    "name": TodoOutcomeDefinitionModel.name,
    "updated_at": TodoOutcomeDefinitionModel.updated_at,
    "code": TodoOutcomeDefinitionModel.code,
}

OUTCOME_SEARCH_FIELDS = (
    TodoOutcomeDefinitionModel.name,
    TodoOutcomeDefinitionModel.code,
)


class SqlAlchemyTodoOutcomeDefinitionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinition:
        model = outcome_entity_to_model(outcome)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return outcome_model_to_entity(model)

    def add_many(self, outcomes: list[TodoOutcomeDefinition]) -> list[TodoOutcomeDefinition]:
        saved: list[TodoOutcomeDefinition] = []
        for outcome in outcomes:
            try:
                saved.append(self.add(outcome))
            except IntegrityError:
                self._session.rollback()
                raise
        return saved

    def get_by_id(
        self, organization_id: UUID, outcome_id: UUID
    ) -> TodoOutcomeDefinition | None:
        model = (
            self._session.query(TodoOutcomeDefinitionModel)
            .filter(
                TodoOutcomeDefinitionModel.organization_id == organization_id,
                TodoOutcomeDefinitionModel.id == outcome_id,
            )
            .one_or_none()
        )
        return outcome_model_to_entity(model) if model else None

    def get_by_code(self, organization_id: UUID, code: str) -> TodoOutcomeDefinition | None:
        model = (
            self._session.query(TodoOutcomeDefinitionModel)
            .filter(
                TodoOutcomeDefinitionModel.organization_id == organization_id,
                TodoOutcomeDefinitionModel.code == code.strip(),
            )
            .one_or_none()
        )
        return outcome_model_to_entity(model) if model else None

    def update(self, outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinition:
        model = (
            self._session.query(TodoOutcomeDefinitionModel)
            .filter(
                TodoOutcomeDefinitionModel.organization_id == outcome.organization_id,
                TodoOutcomeDefinitionModel.id == outcome.id,
            )
            .one()
        )
        update_outcome_model_from_entity(model, outcome)
        self._session.flush()
        self._session.refresh(model)
        return outcome_model_to_entity(model)

    def count_by_organization(self, organization_id: UUID) -> int:
        return (
            self._session.query(TodoOutcomeDefinitionModel)
            .filter(TodoOutcomeDefinitionModel.organization_id == organization_id)
            .count()
        )

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: str = "sort_order",
        sort_dir: str = "asc",
    ) -> OutcomeListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(TodoOutcomeDefinitionModel).filter(
            TodoOutcomeDefinitionModel.organization_id == organization_id,
        )

        if is_active is not None:
            query = query.filter(TodoOutcomeDefinitionModel.is_active == is_active)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(*[field.ilike(pattern) for field in OUTCOME_SEARCH_FIELDS])
            )

        total = query.count()
        sort_column = OUTCOME_SORT_FIELDS.get(sort_by, TodoOutcomeDefinitionModel.sort_order)
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "asc",
            tie_breaker=TodoOutcomeDefinitionModel.id,
        )
        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return OutcomeListResult(
            items=[outcome_model_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )
