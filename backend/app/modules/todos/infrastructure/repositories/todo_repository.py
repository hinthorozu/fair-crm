from datetime import datetime
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

NON_OVERDUE_STATUSES = (TodoStatus.DONE, TodoStatus.ARCHIVED)


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

    def delete_by_id(self, organization_id: UUID, todo_id: UUID) -> bool:
        model = (
            self._session.query(TodoModel)
            .filter(
                TodoModel.organization_id == organization_id,
                TodoModel.id == todo_id,
            )
            .one_or_none()
        )
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        assignee_user_id: UUID | None = None,
        created_by: UUID | None = None,
        is_overdue: bool | None = None,
        include_archived: bool = False,
        now: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "updated_at",
        sort_dir: str = "desc",
    ) -> TodoListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(TodoModel).filter(
            TodoModel.organization_id == organization_id,
        )
        if not include_archived:
            query = query.filter(TodoModel.status != TodoStatus.ARCHIVED)
        if status:
            query = query.filter(TodoModel.status == status.strip())
        if priority:
            query = query.filter(TodoModel.priority == priority.strip())
        if category:
            query = query.filter(TodoModel.category == category.strip())
        if assignee_user_id is not None:
            query = query.filter(TodoModel.assignee_user_id == assignee_user_id)
        if created_by is not None:
            query = query.filter(TodoModel.created_by == created_by)
        if is_overdue is not None:
            if now is None:
                raise ValueError("now is required when filtering by is_overdue")
            overdue_condition = (
                TodoModel.deadline.isnot(None),
                TodoModel.deadline < now,
                TodoModel.status.notin_(NON_OVERDUE_STATUSES),
            )
            if is_overdue:
                query = query.filter(*overdue_condition)
            else:
                query = query.filter(
                    or_(
                        TodoModel.deadline.is_(None),
                        TodoModel.deadline >= now,
                        TodoModel.status.in_(NON_OVERDUE_STATUSES),
                    )
                )
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
