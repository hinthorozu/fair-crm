from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.todos.application.commands import ListTodosQuery, TodoListResultDto
from app.modules.todos.application.mappers import list_result_to_dto
from app.modules.todos.domain.ports import TodoRepository

ALLOWED_SORT_FIELDS = frozenset(
    {
        "title",
        "updated_at",
        "deadline",
        "status",
        "priority",
        "created_at",
    }
)
DEFAULT_SORT_FIELD = "updated_at"
DEFAULT_SORT_DIRECTION = "desc"


class ListTodosUseCase:
    def __init__(self, repository: TodoRepository) -> None:
        self._repository = repository

    def execute(self, query: ListTodosQuery) -> TodoListResultDto:
        page_params = normalize_page_params(query.page, query.page_size)
        requested = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._repository.list_by_organization(
            query.organization_id,
            search=query.search,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=requested,
            sort_dir=sort_dir,
            exclude_archived=True,
        )
        return list_result_to_dto(result)
