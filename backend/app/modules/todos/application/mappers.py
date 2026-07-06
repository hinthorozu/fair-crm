from datetime import UTC, datetime

from app.modules.todos.application.commands import TodoListResultDto, TodoResult
from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.overdue import is_todo_overdue
from app.modules.todos.domain.ports import TodoListResult


def todo_to_result(todo: Todo, *, now: datetime | None = None) -> TodoResult:
    resolved_now = now or datetime.now(tz=UTC)
    return TodoResult(
        id=todo.id,
        organization_id=todo.organization_id,
        title=todo.title,
        description=todo.description,
        status=todo.status,
        priority=todo.priority,
        category=todo.category,
        deadline=todo.deadline,
        assignee_user_id=todo.assignee_user_id,
        created_by=todo.created_by,
        updated_by=todo.updated_by,
        archived_at=todo.archived_at,
        completed_at=todo.completed_at,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        is_overdue=is_todo_overdue(todo, now=resolved_now),
    )


def list_result_to_dto(result: TodoListResult, *, now: datetime | None = None) -> TodoListResultDto:
    resolved_now = now or datetime.now(tz=UTC)
    return TodoListResultDto(
        items=[todo_to_result(item, now=resolved_now) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
