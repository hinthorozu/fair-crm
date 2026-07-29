from __future__ import annotations

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.step_commands import DeleteTodoStepCommand
from app.modules.todos.domain.exceptions import TodoNotFoundError, TodoStepNotFoundError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.infrastructure.repositories.todo_step_repository import (
    SqlAlchemyTodoStepRepository,
)

PERMISSION_UPDATE = "fair_crm.todos.update"


class DeleteTodoStepUseCase:
    def __init__(
        self,
        todo_repository: TodoRepository,
        step_repository: SqlAlchemyTodoStepRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._todo_repository = todo_repository
        self._step_repository = step_repository
        self._authorization = authorization

    def execute(self, command: DeleteTodoStepCommand) -> None:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        todo = self._todo_repository.get_by_id(command.organization_id, command.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")

        step = self._step_repository.get_by_id(
            command.organization_id, command.todo_id, command.step_id
        )
        if step is None:
            raise TodoStepNotFoundError("Todo step not found")

        self._step_repository.delete(
            command.organization_id, command.todo_id, command.step_id
        )
