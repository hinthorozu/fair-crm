from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.commands import DeleteTodoCommand
from app.modules.todos.domain.exceptions import TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository

PERMISSION_DELETE = "fair_crm.todos.delete"


class DeleteTodoUseCase:
    def __init__(
        self,
        repository: TodoRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: DeleteTodoCommand) -> None:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        todo = self._repository.get_by_id(command.organization_id, command.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")

        deleted = self._repository.delete_by_id(command.organization_id, command.todo_id)
        if not deleted:
            raise TodoNotFoundError("Todo not found")

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.todo.deleted",
            resource_type="todo",
            resource_id=str(command.todo_id),
            metadata={"user_id": str(command.user_id), "title": todo.title},
        )
