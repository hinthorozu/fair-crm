from __future__ import annotations

from app.modules.todos.application.step_commands import TodoStepResult
from app.modules.todos.domain.step_entities import TodoStep


def step_to_result(step: TodoStep) -> TodoStepResult:
    return TodoStepResult(
        id=step.id,
        organization_id=step.organization_id,
        todo_id=step.todo_id,
        title=step.title,
        sort_order=step.sort_order,
        is_completed=step.is_completed,
        created_at=step.created_at,
        updated_at=step.updated_at,
    )
