from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.commands import TodoResult, UpdateTodoCommand
from app.modules.todos.application.mappers import todo_to_result
from app.modules.todos.domain.exceptions import TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository

PERMISSION_UPDATE = "fair_crm.todos.update"


class UpdateTodoUseCase:
    def __init__(
        self,
        repository: TodoRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateTodoCommand) -> TodoResult:
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
        todo.update_fields(
            now=now,
            updated_by=command.user_id,
            title=command.title,
            description=command.description,
            status=command.status,
            priority=command.priority,
            category=command.category,
            deadline=command.deadline,
            assignee_user_id=command.assignee_user_id,
            set_description=command.set_description,
            set_deadline=command.set_deadline,
            set_assignee_user_id=command.set_assignee_user_id,
        )

        saved = self._repository.update(todo)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.todo.updated",
            resource_type="todo",
            resource_id=str(saved.id),
            new_values={"title": saved.title, "status": saved.status},
            metadata={"user_id": str(command.user_id)},
        )

        return todo_to_result(saved)
