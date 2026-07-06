from datetime import UTC, datetime

from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.value_objects import TodoStatus

NON_OVERDUE_STATUSES = frozenset({TodoStatus.DONE, TodoStatus.ARCHIVED})


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def is_todo_overdue(todo: Todo, *, now: datetime) -> bool:
    if todo.deadline is None:
        return False
    if todo.status in NON_OVERDUE_STATUSES:
        return False
    return _as_utc(todo.deadline) < _as_utc(now)
