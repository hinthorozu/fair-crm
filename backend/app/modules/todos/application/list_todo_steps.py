from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.step_commands import (
    ListTodoStepsQuery,
    TodoStepResult,
)
from app.modules.todos.application.step_mappers import step_to_result
from app.modules.todos.domain.exceptions import TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.infrastructure.repositories.todo_step_repository import (
    SqlAlchemyTodoStepRepository,
)

PERMISSION_READ = "fair_crm.todos.read"


class ListTodoStepsUseCase:
    def __init__(
        self,
        todo_repository: TodoRepository,
        step_repository: SqlAlchemyTodoStepRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._todo_repository = todo_repository
        self._step_repository = step_repository
        self._authorization = authorization

    def execute(self, query: ListTodoStepsQuery) -> list[TodoStepResult]:
        if not self._authorization.check_permission(
            organization_id=query.organization_id,
            user_id=query.user_id,
            permission_code=PERMISSION_READ,
            access_token=query.access_token,
        ):
            raise ForbiddenError("Permission denied")

        todo = self._todo_repository.get_by_id(query.organization_id, query.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")

        steps = self._step_repository.list_by_todo(query.organization_id, query.todo_id)
        return [step_to_result(step) for step in steps]
