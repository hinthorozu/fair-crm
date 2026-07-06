from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.todos.domain.worklist_entities import TodoWorklistState
from app.modules.todos.infrastructure.persistence.models import TodoWorklistStateModel
from app.modules.todos.infrastructure.persistence.worklist_mappers import (
    update_worklist_state_model_from_entity,
    worklist_state_entity_to_model,
    worklist_state_model_to_entity,
)


class SqlAlchemyTodoWorklistStateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, state: TodoWorklistState) -> TodoWorklistState:
        model = worklist_state_entity_to_model(state)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return worklist_state_model_to_entity(model)

    def get_by_todo_and_customer(
        self,
        organization_id: UUID,
        todo_id: UUID,
        customer_id: UUID,
    ) -> TodoWorklistState | None:
        model = (
            self._session.query(TodoWorklistStateModel)
            .filter(
                TodoWorklistStateModel.organization_id == organization_id,
                TodoWorklistStateModel.todo_id == todo_id,
                TodoWorklistStateModel.customer_id == customer_id,
            )
            .one_or_none()
        )
        return worklist_state_model_to_entity(model) if model else None

    def update(self, state: TodoWorklistState) -> TodoWorklistState:
        model = (
            self._session.query(TodoWorklistStateModel)
            .filter(
                TodoWorklistStateModel.organization_id == state.organization_id,
                TodoWorklistStateModel.id == state.id,
            )
            .one()
        )
        update_worklist_state_model_from_entity(model, state)
        self._session.flush()
        self._session.refresh(model)
        return worklist_state_model_to_entity(model)

    def exists_for_todo(self, organization_id: UUID, todo_id: UUID) -> bool:
        return (
            self._session.query(TodoWorklistStateModel.id)
            .filter(
                TodoWorklistStateModel.organization_id == organization_id,
                TodoWorklistStateModel.todo_id == todo_id,
            )
            .first()
            is not None
        )

    def count_by_todo(self, organization_id: UUID, todo_id: UUID) -> int:
        return (
            self._session.query(TodoWorklistStateModel)
            .filter(
                TodoWorklistStateModel.organization_id == organization_id,
                TodoWorklistStateModel.todo_id == todo_id,
            )
            .count()
        )
