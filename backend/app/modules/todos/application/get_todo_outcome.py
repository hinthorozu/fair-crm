from app.modules.todos.application.outcome_commands import GetTodoOutcomeQuery, TodoOutcomeResult
from app.modules.todos.application.outcome_mappers import outcome_to_result
from app.modules.todos.domain.exceptions import TodoOutcomeDefinitionNotFoundError
from app.modules.todos.domain.worklist_ports import TodoOutcomeDefinitionRepository


class GetTodoOutcomeUseCase:
    def __init__(self, repository: TodoOutcomeDefinitionRepository) -> None:
        self._repository = repository

    def execute(self, query: GetTodoOutcomeQuery) -> TodoOutcomeResult:
        outcome = self._repository.get_by_id(query.organization_id, query.outcome_id)
        if outcome is None:
            raise TodoOutcomeDefinitionNotFoundError("Outcome not found")
        return outcome_to_result(outcome)
