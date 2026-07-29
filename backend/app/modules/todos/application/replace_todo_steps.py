from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.step_commands import (
    ReplaceTodoStepsCommand,
    TodoStepResult,
)
from app.modules.todos.application.step_mappers import step_to_result
from app.modules.todos.domain.exceptions import InvalidTodoStepTitleError, TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.domain.step_entities import TodoStep
from app.modules.todos.infrastructure.repositories.todo_step_repository import (
    SqlAlchemyTodoStepRepository,
)

PERMISSION_UPDATE = "fair_crm.todos.update"
PERMISSION_CREATE = "fair_crm.todos.create"


class ReplaceTodoStepsUseCase:
    """Replace-all checklist for a todo (form save). Preserves completion on kept ids."""

    def __init__(
        self,
        todo_repository: TodoRepository,
        step_repository: SqlAlchemyTodoStepRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._todo_repository = todo_repository
        self._step_repository = step_repository
        self._authorization = authorization

    def execute(self, command: ReplaceTodoStepsCommand) -> list[TodoStepResult]:
        if not (
            self._authorization.check_permission(
                organization_id=command.organization_id,
                user_id=command.user_id,
                permission_code=PERMISSION_UPDATE,
                access_token=command.access_token,
            )
            or self._authorization.check_permission(
                organization_id=command.organization_id,
                user_id=command.user_id,
                permission_code=PERMISSION_CREATE,
                access_token=command.access_token,
            )
        ):
            raise ForbiddenError("Permission denied")

        todo = self._todo_repository.get_by_id(command.organization_id, command.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")

        now = datetime.now(tz=UTC)
        existing = {
            step.id: step
            for step in self._step_repository.list_by_todo(
                command.organization_id, command.todo_id
            )
        }

        cleaned_items: list[tuple[object, str]] = []
        for item in command.steps:
            title = item.title.strip()
            if not title:
                continue
            if len(title) > 500:
                raise InvalidTodoStepTitleError("Step title is too long")
            cleaned_items.append((item.id, title))

        keep_ids = set()
        result_steps: list[TodoStep] = []

        for sort_order, (step_id, title) in enumerate(cleaned_items):
            if step_id is not None and step_id in existing:
                step = existing[step_id]
                step.rename(title=title, now=now)
                step.set_sort_order(sort_order=sort_order, now=now)
                saved = self._step_repository.update(step)
                keep_ids.add(step.id)
                result_steps.append(saved)
            else:
                created = TodoStep.create(
                    organization_id=command.organization_id,
                    todo_id=command.todo_id,
                    title=title,
                    sort_order=sort_order,
                    now=now,
                )
                saved = self._step_repository.add(created)
                keep_ids.add(saved.id)
                result_steps.append(saved)

        orphan_ids = [step_id for step_id in existing if step_id not in keep_ids]
        self._step_repository.delete_ids(
            command.organization_id, command.todo_id, orphan_ids
        )

        return [step_to_result(step) for step in result_steps]
