from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.worklist_entities import TodoWorklistState
from app.modules.todos.domain.worklist_query import TodoWorklistListResult, TodoWorklistProgress
from app.modules.todos.domain.worklist_value_objects import WorklistFilter


class OutcomeListResult:
    def __init__(
        self,
        *,
        items: list[TodoOutcomeDefinition],
        page: int,
        page_size: int,
        total: int,
        total_pages: int,
    ) -> None:
        self.items = items
        self.page = page
        self.page_size = page_size
        self.total = total
        self.total_pages = total_pages


class TodoOutcomeDefinitionRepository(Protocol):
    def add(self, outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinition: ...

    def get_by_id(
        self, organization_id: UUID, outcome_id: UUID
    ) -> TodoOutcomeDefinition | None: ...

    def get_by_code(
        self, organization_id: UUID, code: str
    ) -> TodoOutcomeDefinition | None: ...

    def update(self, outcome: TodoOutcomeDefinition) -> TodoOutcomeDefinition: ...

    def count_by_organization(self, organization_id: UUID) -> int: ...

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: str = "sort_order",
        sort_dir: str = "asc",
    ) -> OutcomeListResult: ...


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


class TodoWorklistQueryRepository(Protocol):
    def list_for_todo(
        self,
        organization_id: UUID,
        todo_id: UUID,
        source_fair_id: UUID,
        *,
        todo_completed_at: datetime | None,
        worklist_filter: WorklistFilter,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "company_name",
        sort_dir: str = "asc",
    ) -> TodoWorklistListResult: ...

    def progress_for_todo(
        self,
        organization_id: UUID,
        todo_id: UUID,
        source_fair_id: UUID,
    ) -> TodoWorklistProgress: ...

    def get_row_for_customer(
        self,
        organization_id: UUID,
        todo_id: UUID,
        source_fair_id: UUID,
        customer_id: UUID,
        *,
        todo_completed_at: datetime | None,
    ) -> TodoWorklistRow | None: ...
