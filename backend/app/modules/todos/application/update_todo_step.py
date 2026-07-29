from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.step_commands import (
    UpdateTodoStepCommand,
    TodoStepResult,
)
from app.modules.todos.application.step_mappers import step_to_result
from app.modules.todos.domain.exceptions import TodoNotFoundError, TodoStepNotFoundError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.infrastructure.repositories.todo_step_repository import (
    SqlAlchemyTodoStepRepository,
)

PERMISSION_UPDATE = "fair_crm.todos.update"


class UpdateTodoStepUseCase:
    def __init__(
        self,
        todo_repository: TodoRepository,
        step_repository: SqlAlchemyTodoStepRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._todo_repository = todo_repository
        self._step_repository = step_repository
        self._authorization = authorization

    def execute(self, command: UpdateTodoStepCommand) -> TodoStepResult:
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

        now = datetime.now(tz=UTC)
        if command.set_title and command.title is not None:
            step.rename(title=command.title, now=now)
        if command.set_is_completed and command.is_completed is not None:
            step.set_completed(is_completed=command.is_completed, now=now)

        saved = self._step_repository.update(step)
        return step_to_result(saved)
