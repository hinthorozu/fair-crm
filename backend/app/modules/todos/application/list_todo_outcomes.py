from app.core.pagination import normalize_sort_direction
from app.modules.todos.application.ensure_default_outcomes import EnsureDefaultOutcomesUseCase
from app.modules.todos.application.outcome_commands import (
    EnsureDefaultOutcomesCommand,
    ListTodoOutcomesQuery,
    TodoOutcomeListResultDto,
)
from app.modules.todos.application.outcome_mappers import outcome_list_to_dto
from app.modules.todos.domain.worklist_ports import TodoOutcomeDefinitionRepository

ALLOWED_SORT_FIELDS = frozenset({"sort_order", "name", "updated_at", "code"})
DEFAULT_SORT_FIELD = "sort_order"
DEFAULT_SORT_DIRECTION = "asc"


class ListTodoOutcomesUseCase:
    def __init__(
        self,
        repository: TodoOutcomeDefinitionRepository,
        ensure_defaults: EnsureDefaultOutcomesUseCase,
    ) -> None:
        self._repository = repository
        self._ensure_defaults = ensure_defaults

    def execute(self, query: ListTodoOutcomesQuery) -> TodoOutcomeListResultDto:
        if query.ensure_defaults:
            self._ensure_defaults.execute(
                EnsureDefaultOutcomesCommand(organization_id=query.organization_id)
            )

        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)
        result = self._repository.list_by_organization(
            query.organization_id,
            is_active=query.is_active,
            search=query.search,
            page=query.page,
            page_size=query.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return outcome_list_to_dto(result)
