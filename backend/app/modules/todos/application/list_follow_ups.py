from app.core.pagination import normalize_sort_direction
from app.modules.todos.application.worklist_commands import FollowUpListResultDto, ListFollowUpsQuery
from app.modules.todos.application.worklist_mappers import follow_up_list_to_dto
from app.modules.todos.domain.worklist_ports import TodoWorklistQueryRepository
from app.modules.todos.domain.worklist_value_objects import FollowUpFilter

ALLOWED_SORT_FIELDS = frozenset(
    {"company_name", "todo_title", "last_activity_at", "follow_up_at", "primary_status"}
)
DEFAULT_SORT_FIELD = "follow_up_at"
DEFAULT_SORT_DIRECTION = "asc"
DEFAULT_FILTER = FollowUpFilter.BUGUN


class ListFollowUpsUseCase:
    def __init__(self, worklist_query_repository: TodoWorklistQueryRepository) -> None:
        self._worklist_query_repository = worklist_query_repository

    def execute(self, query: ListFollowUpsQuery) -> FollowUpListResultDto:
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)
        follow_up_filter = query.follow_up_filter or DEFAULT_FILTER

        result = self._worklist_query_repository.list_follow_ups(
            query.organization_id,
            follow_up_filter=follow_up_filter,
            search=query.search,
            page=query.page,
            page_size=query.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return follow_up_list_to_dto(result)
