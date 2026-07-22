from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.activities.domain.value_objects import (
    ActivitySource,
    ActivityStatus,
    ActivityType,
)
from app.modules.todos.application.commands import CompleteTodoCommand, TodoResult
from app.modules.todos.application.mappers import todo_to_result
from app.modules.todos.application.update_todo import PERMISSION_UPDATE
from app.modules.todos.domain.exceptions import TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.domain.value_objects import TodoStatus


class CompleteTodoUseCase:
    """Mark Todo done and create exactly one task_completed Activity in one DB transaction.

    Activity creation must NOT happen from CreateTodo / UpdateTodo — only here.
    get_db commits once at request end; any failure rolls back both sides.
    """

    def __init__(
        self,
        repository: TodoRepository,
        activity_repository: ActivityRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._activity_repository = activity_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CompleteTodoCommand) -> TodoResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        todo = self._repository.get_by_id(command.organization_id, command.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")

        now = datetime.now(tz=UTC)

        if todo.status == TodoStatus.DONE:
            return todo_to_result(todo, now=now)

        existing_activity = self._activity_repository.get_task_completed_by_todo_id(
            command.organization_id, todo.id
        )
        if existing_activity is not None:
            todo.complete(now=now, updated_by=command.user_id)
            saved = self._repository.update(todo)
            return todo_to_result(saved, now=now)

        note = command.note.strip() if command.note and command.note.strip() else None

        # Snapshot links at completion time (customer/fair may be null).
        activity = Activity.create(
            organization_id=command.organization_id,
            customer_id=todo.customer_id,
            fair_id=todo.source_fair_id,
            todo_id=todo.id,
            activity_type=ActivityType.TASK_COMPLETED,
            subject=f"Görev tamamlandı: {todo.title}",
            description=note,
            activity_date=now,
            status=ActivityStatus.COMPLETED,
            source=ActivitySource.SYSTEM,
            metadata_json={"completed_by": str(command.user_id)},
            now=now,
        )

        # Persist Activity first, then mark Todo done — same request session/transaction.
        # If either fails, get_db rolls back both (Todo stays open, no Activity).
        self._activity_repository.add(activity)
        todo.complete(now=now, updated_by=command.user_id)
        saved = self._repository.update(todo)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.todo.completed",
            resource_type="todo",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        return todo_to_result(saved, now=now)
