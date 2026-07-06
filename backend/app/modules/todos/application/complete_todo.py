from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.commands import CompleteTodoCommand, TodoResult
from app.modules.todos.application.mappers import todo_to_result
from app.modules.todos.application.update_todo import PERMISSION_UPDATE
from app.modules.todos.domain.exceptions import TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository


class CompleteTodoUseCase:
    def __init__(
        self,
        repository: TodoRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
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
