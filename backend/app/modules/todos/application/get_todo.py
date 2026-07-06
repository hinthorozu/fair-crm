from app.modules.todos.application.commands import GetTodoQuery, TodoResult
from app.modules.todos.application.mappers import todo_to_result
from app.modules.todos.domain.exceptions import TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository


class GetTodoUseCase:
    def __init__(self, repository: TodoRepository) -> None:
        self._repository = repository

    def execute(self, query: GetTodoQuery) -> TodoResult:
        todo = self._repository.get_by_id(query.organization_id, query.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")
        return todo_to_result(todo)
