from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.modules.todos.application.outcome_commands import EnsureDefaultOutcomesCommand
from app.modules.todos.application.outcome_default_seed import DEFAULT_OUTCOME_SEEDS
from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.worklist_ports import TodoOutcomeDefinitionRepository


class EnsureDefaultOutcomesUseCase:
    def __init__(self, repository: TodoOutcomeDefinitionRepository) -> None:
        self._repository = repository

    def execute(self, command: EnsureDefaultOutcomesCommand) -> None:
        if self._repository.count_by_organization(command.organization_id) > 0:
            return

        now = datetime.now(tz=UTC)
        for spec in DEFAULT_OUTCOME_SEEDS:
            if self._repository.get_by_code(command.organization_id, spec.code) is not None:
                continue
            outcome = TodoOutcomeDefinition.create(
                organization_id=command.organization_id,
                name=spec.name,
                code=spec.code,
                primary_worklist_status=spec.primary_worklist_status,
                description=spec.description,
                sort_order=spec.sort_order,
                requires_action=spec.requires_action,
                marks_data_problem=spec.marks_data_problem,
                now=now,
            )
            try:
                self._repository.add(outcome)
            except IntegrityError:
                return
