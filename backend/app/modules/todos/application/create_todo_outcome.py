from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.outcome_commands import CreateTodoOutcomeCommand, TodoOutcomeResult
from app.modules.todos.application.outcome_mappers import outcome_to_result
from app.modules.todos.domain.exceptions import DuplicateOutcomeCodeError
from app.modules.todos.domain.outcome_entities import TodoOutcomeDefinition
from app.modules.todos.domain.worklist_ports import TodoOutcomeDefinitionRepository

PERMISSION_CREATE = "fair_crm.todos.outcomes.create"


class CreateTodoOutcomeUseCase:
    def __init__(
        self,
        repository: TodoOutcomeDefinitionRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateTodoOutcomeCommand) -> TodoOutcomeResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        if self._repository.get_by_code(command.organization_id, command.code) is not None:
            raise DuplicateOutcomeCodeError("Outcome code already exists")

        now = datetime.now(tz=UTC)
        outcome = TodoOutcomeDefinition.create(
            organization_id=command.organization_id,
            name=command.name,
            code=command.code,
            primary_worklist_status=command.primary_worklist_status,
            description=command.description,
            sort_order=command.sort_order,
            requires_action=command.requires_action,
            marks_data_problem=command.marks_data_problem,
            is_active=command.is_active,
            now=now,
        )
        saved = self._repository.add(outcome)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.todo_outcome.created",
            resource_type="todo_outcome",
            resource_id=str(saved.id),
            new_values={"code": saved.code, "name": saved.name},
            metadata={"user_id": str(command.user_id)},
        )

        return outcome_to_result(saved)
