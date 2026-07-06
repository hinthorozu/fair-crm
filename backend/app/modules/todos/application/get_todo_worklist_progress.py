from app.modules.todos.application.worklist_commands import GetTodoWorklistProgressQuery, TodoWorklistProgressResult
from app.modules.todos.application.worklist_mappers import worklist_progress_to_result
from app.modules.todos.domain.exceptions import TodoMissingSourceFairError, TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.domain.worklist_ports import TodoWorklistQueryRepository


class GetTodoWorklistProgressUseCase:
    def __init__(
        self,
        todo_repository: TodoRepository,
        worklist_query_repository: TodoWorklistQueryRepository,
    ) -> None:
        self._todo_repository = todo_repository
        self._worklist_query_repository = worklist_query_repository

    def execute(self, query: GetTodoWorklistProgressQuery) -> TodoWorklistProgressResult:
        todo = self._todo_repository.get_by_id(query.organization_id, query.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")
        if todo.source_fair_id is None:
            raise TodoMissingSourceFairError("Todo source fair is required for worklist")

        progress = self._worklist_query_repository.progress_for_todo(
            query.organization_id,
            query.todo_id,
            todo.source_fair_id,
        )
        return worklist_progress_to_result(progress)
