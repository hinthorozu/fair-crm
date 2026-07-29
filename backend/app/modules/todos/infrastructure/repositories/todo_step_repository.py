from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.todos.domain.step_entities import TodoStep
from app.modules.todos.infrastructure.persistence.models import TodoStepModel
from app.modules.todos.infrastructure.persistence.step_mappers import (
    step_entity_to_model,
    step_model_to_entity,
    update_step_model_from_entity,
)


class SqlAlchemyTodoStepRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_todo(self, organization_id: UUID, todo_id: UUID) -> list[TodoStep]:
        rows = (
            self._session.query(TodoStepModel)
            .filter(
                TodoStepModel.organization_id == organization_id,
                TodoStepModel.todo_id == todo_id,
            )
            .order_by(TodoStepModel.sort_order.asc(), TodoStepModel.created_at.asc())
            .all()
        )
        return [step_model_to_entity(row) for row in rows]

    def get_by_id(
        self, organization_id: UUID, todo_id: UUID, step_id: UUID
    ) -> TodoStep | None:
        model = (
            self._session.query(TodoStepModel)
            .filter(
                TodoStepModel.organization_id == organization_id,
                TodoStepModel.todo_id == todo_id,
                TodoStepModel.id == step_id,
            )
            .one_or_none()
        )
        return step_model_to_entity(model) if model else None

    def add(self, step: TodoStep) -> TodoStep:
        model = step_entity_to_model(step)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return step_model_to_entity(model)

    def update(self, step: TodoStep) -> TodoStep:
        model = (
            self._session.query(TodoStepModel)
            .filter(
                TodoStepModel.organization_id == step.organization_id,
                TodoStepModel.todo_id == step.todo_id,
                TodoStepModel.id == step.id,
            )
            .one()
        )
        update_step_model_from_entity(model, step)
        self._session.flush()
        self._session.refresh(model)
        return step_model_to_entity(model)

    def delete(self, organization_id: UUID, todo_id: UUID, step_id: UUID) -> None:
        model = (
            self._session.query(TodoStepModel)
            .filter(
                TodoStepModel.organization_id == organization_id,
                TodoStepModel.todo_id == todo_id,
                TodoStepModel.id == step_id,
            )
            .one_or_none()
        )
        if model is not None:
            self._session.delete(model)
            self._session.flush()

    def delete_ids(self, organization_id: UUID, todo_id: UUID, step_ids: list[UUID]) -> None:
        if not step_ids:
            return
        (
            self._session.query(TodoStepModel)
            .filter(
                TodoStepModel.organization_id == organization_id,
                TodoStepModel.todo_id == todo_id,
                TodoStepModel.id.in_(step_ids),
            )
            .delete(synchronize_session=False)
        )
        self._session.flush()
