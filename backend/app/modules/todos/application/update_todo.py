from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.domain.ports import FairRepository
from app.modules.todos.application.commands import TodoResult, UpdateTodoCommand
from app.modules.todos.application.mappers import todo_to_result
from app.modules.todos.application.validators import ensure_source_fair_exists
from app.modules.todos.domain.exceptions import TodoNotFoundError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.domain.worklist_ports import TodoWorklistStateRepository

PERMISSION_UPDATE = "fair_crm.todos.update"


class UpdateTodoUseCase:
    def __init__(
        self,
        repository: TodoRepository,
        fair_repository: FairRepository,
        worklist_state_repository: TodoWorklistStateRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._fair_repository = fair_repository
        self._worklist_state_repository = worklist_state_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateTodoCommand) -> TodoResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        todo = self._repository.get_by_id(command.organization_id, command.todo_id)
        if todo is None:
            raise TodoNotFoundError("Todo not found")

        if command.set_source_fair_id and command.source_fair_id is not None:
            ensure_source_fair_exists(
                self._fair_repository,
                command.organization_id,
                command.source_fair_id,
            )

        has_worklist_states = self._worklist_state_repository.exists_for_todo(
            command.organization_id,
            command.todo_id,
        )

        now = datetime.now(tz=UTC)
        todo.update_fields(
            now=now,
            updated_by=command.user_id,
            title=command.title,
            description=command.description,
            status=command.status,
            priority=command.priority,
            category=command.category,
            deadline=command.deadline,
            assignee_user_id=command.assignee_user_id,
            source_fair_id=command.source_fair_id,
            set_description=command.set_description,
            set_deadline=command.set_deadline,
            set_assignee_user_id=command.set_assignee_user_id,
            set_source_fair_id=command.set_source_fair_id,
            has_worklist_states=has_worklist_states,
        )

        saved = self._repository.update(todo)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.todo.updated",
            resource_type="todo",
            resource_id=str(saved.id),
            new_values={"title": saved.title, "status": saved.status},
            metadata={"user_id": str(command.user_id)},
        )

        return todo_to_result(saved, now=now)
