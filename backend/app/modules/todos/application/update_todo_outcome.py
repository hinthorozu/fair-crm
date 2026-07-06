from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.todos.application.outcome_commands import TodoOutcomeResult, UpdateTodoOutcomeCommand
from app.modules.todos.application.outcome_mappers import outcome_to_result
from app.modules.todos.domain.exceptions import TodoOutcomeDefinitionNotFoundError
from app.modules.todos.domain.worklist_ports import TodoOutcomeDefinitionRepository

PERMISSION_UPDATE = "fair_crm.todos.outcomes.update"


class UpdateTodoOutcomeUseCase:
    def __init__(
        self,
        repository: TodoOutcomeDefinitionRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateTodoOutcomeCommand) -> TodoOutcomeResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        outcome = self._repository.get_by_id(command.organization_id, command.outcome_id)
        if outcome is None:
            raise TodoOutcomeDefinitionNotFoundError("Outcome not found")

        now = datetime.now(tz=UTC)
        outcome.update_fields(
            now=now,
            name=command.name,
            description=command.description,
            set_description=command.set_description,
            primary_worklist_status=command.primary_worklist_status,
            requires_action=command.requires_action,
            marks_data_problem=command.marks_data_problem,
            sort_order=command.sort_order,
            is_active=command.is_active,
        )
        saved = self._repository.update(outcome)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.todo_outcome.updated",
            resource_type="todo_outcome",
            resource_id=str(saved.id),
            new_values={"code": saved.code, "is_active": saved.is_active},
            metadata={"user_id": str(command.user_id)},
        )

        return outcome_to_result(saved)
