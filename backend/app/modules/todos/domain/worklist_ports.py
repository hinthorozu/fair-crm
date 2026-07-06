from typing import Protocol
from uuid import UUID

from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.worklist_entities import TodoWorklistState


class TodoOutcomeDefinitionRepository(Protocol):
    def add(self, outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinition: ...

    def get_by_id(
        self, organization_id: UUID, outcome_id: UUID
    ) -> TodoOutcomeDefinition | None: ...

    def get_by_code(
        self, organization_id: UUID, code: str
    ) -> TodoOutcomeDefinition | None: ...

    def update(self, outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinition: ...


class TodoWorklistStateRepository(Protocol):
    def add(self, state: TodoWorklistState) -> TodoWorklistState: ...

    def get_by_todo_and_customer(
        self,
        organization_id: UUID,
        todo_id: UUID,
        customer_id: UUID,
    ) -> TodoWorklistState | None: ...

    def update(self, state: TodoWorklistState) -> TodoWorklistState: ...

    def exists_for_todo(self, organization_id: UUID, todo_id: UUID) -> bool: ...

    def count_by_todo(self, organization_id: UUID, todo_id: UUID) -> int: ...
