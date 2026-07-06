from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.domain.ports import FairRepository
from app.modules.todos.application.commands import CreateTodoCommand, TodoResult
from app.modules.todos.application.mappers import todo_to_result
from app.modules.todos.application.validators import ensure_source_fair_exists
from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.ports import TodoRepository

PERMISSION_CREATE = "fair_crm.todos.create"


class CreateTodoUseCase:
    def __init__(
        self,
        repository: TodoRepository,
        fair_repository: FairRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._fair_repository = fair_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateTodoCommand) -> TodoResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        if command.source_fair_id is not None:
            ensure_source_fair_exists(
                self._fair_repository,
                command.organization_id,
                command.source_fair_id,
            )

        now = datetime.now(tz=UTC)
        todo = Todo.create(
            organization_id=command.organization_id,
            title=command.title,
            created_by=command.user_id,
            description=command.description,
            status=command.status,
            priority=command.priority,
            category=command.category,
            deadline=command.deadline,
            assignee_user_id=command.assignee_user_id,
            source_fair_id=command.source_fair_id,
            now=now,
        )
        saved = self._repository.add(todo)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.todo.created",
            resource_type="todo",
            resource_id=str(saved.id),
            new_values={"title": saved.title, "status": saved.status},
            metadata={"user_id": str(command.user_id)},
        )

        return todo_to_result(saved, now=now)
