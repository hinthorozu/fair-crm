from __future__ import annotations

from app.modules.todos.domain.step_entities import TodoStep
from app.modules.todos.infrastructure.persistence.models import TodoStepModel


def step_model_to_entity(model: TodoStepModel) -> TodoStep:
    return TodoStep(
        id=model.id,
        organization_id=model.organization_id,
        todo_id=model.todo_id,
        title=model.title,
        sort_order=model.sort_order,
        is_completed=model.is_completed,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def step_entity_to_model(entity: TodoStep) -> TodoStepModel:
    return TodoStepModel(
        id=entity.id,
        organization_id=entity.organization_id,
        todo_id=entity.todo_id,
        title=entity.title,
        sort_order=entity.sort_order,
        is_completed=entity.is_completed,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def update_step_model_from_entity(model: TodoStepModel, entity: TodoStep) -> None:
    model.title = entity.title
    model.sort_order = entity.sort_order
    model.is_completed = entity.is_completed
    model.updated_at = entity.updated_at
