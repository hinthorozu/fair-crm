from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.infrastructure.persistence.worklist_mappers import (
    outcome_entity_to_model,
    outcome_model_to_entity,
    update_outcome_model_from_entity,
)
from app.modules.todos.infrastructure.persistence.models import TodoOutcomeDefinitionModel


class SqlAlchemyTodoOutcomeDefinitionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinition:
        model = outcome_entity_to_model(outcome)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return outcome_model_to_entity(model)

    def get_by_id(
        self, organization_id: UUID, outcome_id: UUID
    ) -> TodoOutcomeDefinition | None:
        model = (
            self._session.query(TodoOutcomeDefinitionModel)
            .filter(
                TodoOutcomeDefinitionModel.organization_id == organization_id,
                TodoOutcomeDefinitionModel.id == outcome_id,
            )
            .one_or_none()
        )
        return outcome_model_to_entity(model) if model else None

    def get_by_code(self, organization_id: UUID, code: str) -> TodoOutcomeDefinition | None:
        model = (
            self._session.query(TodoOutcomeDefinitionModel)
            .filter(
                TodoOutcomeDefinitionModel.organization_id == organization_id,
                TodoOutcomeDefinitionModel.code == code.strip(),
            )
            .one_or_none()
        )
        return outcome_model_to_entity(model) if model else None

    def update(self, outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinition:
        model = (
            self._session.query(TodoOutcomeDefinitionModel)
            .filter(
                TodoOutcomeDefinitionModel.organization_id == outcome.organization_id,
                TodoOutcomeDefinitionModel.id == outcome.id,
            )
            .one()
        )
        update_outcome_model_from_entity(model, outcome)
        self._session.flush()
        self._session.refresh(model)
        return outcome_model_to_entity(model)
