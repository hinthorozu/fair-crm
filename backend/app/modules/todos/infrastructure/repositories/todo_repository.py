from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.ports import TodoListResult
from app.modules.todos.domain.value_objects import TodoStatus
from app.modules.todos.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.todos.infrastructure.persistence.models import TodoModel

TODO_SORT_FIELDS = {
    "title": TodoModel.title,
    "updated_at": TodoModel.updated_at,
    "deadline": TodoModel.deadline,
    "status": TodoModel.status,
    "priority": TodoModel.priority,
    "created_at": TodoModel.created_at,
}

SEARCH_FIELDS = (
    TodoModel.title,
    TodoModel.description,
)


class SqlAlchemyTodoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, todo: Todo) -> Todo:
        model = entity_to_model(todo)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def get_by_id(self, organization_id: UUID, todo_id: UUID) -> Todo | None:
        model = (
            self._session.query(TodoModel)
            .filter(
                TodoModel.organization_id == organization_id,
                TodoModel.id == todo_id,
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def update(self, todo: Todo) -> Todo:
        model = (
            self._session.query(TodoModel)
            .filter(
                TodoModel.organization_id == todo.organization_id,
                TodoModel.id == todo.id,
            )
            .one()
        )
        update_model_from_entity(model, todo)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "updated_at",
        sort_dir: str = "desc",
        exclude_archived: bool = True,
    ) -> TodoListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(TodoModel).filter(
            TodoModel.organization_id == organization_id,
        )
        if exclude_archived:
            query = query.filter(TodoModel.status != TodoStatus.ARCHIVED)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(*[field.ilike(pattern) for field in SEARCH_FIELDS]))

        total = query.count()
        sort_column = TODO_SORT_FIELDS.get(sort_by, TodoModel.updated_at)
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "desc",
            tie_breaker=TodoModel.id,
        )

        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return TodoListResult(
            items=[model_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )
