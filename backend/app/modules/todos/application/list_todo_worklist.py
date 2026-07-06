from app.core.pagination import normalize_sort_direction
from app.modules.todos.application.worklist_commands import ListTodoWorklistQuery, TodoWorklistListResultDto
from app.modules.todos.application.worklist_mappers import worklist_list_to_dto
from app.modules.todos.domain.exceptions import TodoMissingSourceFairError, TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.domain.worklist_ports import TodoWorklistQueryRepository
from app.modules.todos.domain.worklist_value_objects import WorklistFilter

ALLOWED_SORT_FIELDS = frozenset({"company_name", "last_activity_at", "follow_up_at", "primary_status"})
DEFAULT_SORT_FIELD = "company_name"
DEFAULT_SORT_DIRECTION = "asc"
DEFAULT_FILTER = WorklistFilter.YAPILMADI


class ListTodoWorklistUseCase:
    def __init__(
        self,
        todo_repository: TodoRepository,
        worklist_query_repository: TodoWorklistQueryRepository,
    ) -> None:
        self._todo_repository = todo_repository
        self._worklist_query_repository = worklist_query_repository

    def execute(self, query: ListTodoWorklistQuery) -> TodoWorklistListResultDto:
        todo = self._todo_repository.get_by_id(query.organization_id, query.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")
        if todo.source_fair_id is None:
            raise TodoMissingSourceFairError("Todo source fair is required for worklist")

        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)
        worklist_filter = query.worklist_filter or DEFAULT_FILTER

        result = self._worklist_query_repository.list_for_todo(
            query.organization_id,
            query.todo_id,
            todo.source_fair_id,
            todo_completed_at=todo.completed_at,
            worklist_filter=worklist_filter,
            search=query.search,
            page=query.page,
            page_size=query.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return worklist_list_to_dto(result)
