from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.ports import FairRepository
from app.modules.operations.domain.entities import Operation
from app.modules.operations.domain.exceptions import InvalidOperationConfigError
from app.modules.operations.domain.handler import (
    HandlerExecutionContext,
    HandlerStartResult,
    HandlerValidationResult,
)
from app.modules.operations.domain.source_normalization import extract_source_ids
from app.modules.operations.domain.value_objects import (
    HandlerCapabilities,
    OperationPriority,
    OperationType,
    RunStatus,
    SourceKind,
)
from app.modules.todos.application.validators import (
    ensure_customer_exists,
    ensure_source_fair_exists,
)
from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.exceptions import InvalidTodoCustomerError
from app.modules.todos.domain.ports import TodoRepository
from app.modules.todos.domain.value_objects import TodoCategory, TodoPriority, TodoStatus


def _parse_optional_uuid(value: Any) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _parse_optional_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


class ManualTaskHandler:
    """Creates a Todo for human work; Operation remains orchestration only."""

    operation_type = OperationType.MANUAL_TASK

    def __init__(
        self,
        todo_repository: TodoRepository | None = None,
        fair_repository: FairRepository | None = None,
        customer_repository: CustomerRepository | None = None,
    ) -> None:
        self._todo_repository = todo_repository
        self._fair_repository = fair_repository
        self._customer_repository = customer_repository

    @property
    def capabilities(self) -> HandlerCapabilities:
        return HandlerCapabilities(
            supports_pause=False,
            supports_resume=False,
            supports_retry=False,
            supports_schedule=True,
            supports_items=False,
            requires_worker=False,
            execution_ready=True,
        )

    def validate_create(
        self,
        *,
        source_kind: str,
        source_config: dict[str, Any],
        type_config: dict[str, Any],
        run_settings: dict[str, Any],
    ) -> HandlerValidationResult:
        _ = run_settings
        errors: list[str] = []

        if source_kind not in {SourceKind.CUSTOMER, SourceKind.NONE, SourceKind.FAIR}:
            errors.append("manual_task supports source kinds: customer, none, fair")

        title = str(type_config.get("title") or "").strip()
        if not title:
            errors.append("type_config.title is required")

        priority = type_config.get("priority", OperationPriority.NORMAL)
        try:
            TodoPriority(str(priority))
        except ValueError:
            errors.append(f"invalid type_config.priority: {priority}")

        customer_id = type_config.get("customer_id")
        if source_kind == SourceKind.CUSTOMER and not customer_id:
            source_customer = (
                source_config.get("customer_id") if isinstance(source_config, dict) else None
            )
            if not source_customer:
                errors.append("customer_id is required when source_kind is customer")

        try:
            if type_config.get("due_at") is not None:
                _parse_optional_datetime(type_config.get("due_at"))
        except (TypeError, ValueError):
            errors.append("type_config.due_at must be an ISO datetime string")

        assignee_raw = type_config.get("assignee_user_id")
        if assignee_raw is None:
            assignee_raw = type_config.get("assigned_user_id")
        try:
            if assignee_raw is not None:
                _parse_optional_uuid(assignee_raw)
        except (TypeError, ValueError):
            errors.append("type_config.assignee_user_id must be a UUID")

        if source_kind == SourceKind.FAIR:
            source_ids = extract_source_ids(source_config)
            if len(source_ids) > 1:
                errors.append(
                    "manual_task fair source supports at most one source_id "
                    "(Todo.source_fair_id is singular)"
                )

        if errors:
            return HandlerValidationResult.failure(*errors)
        return HandlerValidationResult.success()

    def validate_start(self, *, operation: Operation) -> HandlerValidationResult:
        # Idempotent re-start is allowed when Todo already linked.
        if operation.related_todo_id is not None:
            return HandlerValidationResult.success()
        return self.validate_create(
            source_kind=operation.source_kind,
            source_config=operation.source_config,
            type_config=operation.type_config,
            run_settings=operation.run_settings,
        )

    def on_start(
        self,
        *,
        operation: Operation,
        run,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        _ = run
        if operation.related_todo_id is not None:
            return HandlerStartResult(
                run_status=RunStatus.COMPLETED,
                total_items=0,
                message="Manual task already linked to Todo",
                result_payload={"related_todo_id": str(operation.related_todo_id)},
                related_todo_id=operation.related_todo_id,
            )

        if self._todo_repository is None:
            raise InvalidOperationConfigError("Todo repository is required for manual_task")

        config = dict(operation.type_config or {})
        title = str(config.get("title") or operation.title).strip()
        description = config.get("description")
        if description is None:
            description = config.get("note")
        if description is None:
            description = operation.description

        due_at = _parse_optional_datetime(config.get("due_at"))
        assignee_raw = config.get("assignee_user_id")
        if assignee_raw is None:
            assignee_raw = config.get("assigned_user_id")
        assignee_user_id = _parse_optional_uuid(assignee_raw)
        priority = str(config.get("priority") or operation.priority or TodoPriority.NORMAL)
        source_fair_id = self._resolve_source_fair_id(operation)
        customer_id = self._resolve_customer_id(operation)

        if source_fair_id is not None:
            if self._fair_repository is None:
                raise InvalidOperationConfigError(
                    "Fair repository is required when linking source_fair_id"
                )
            ensure_source_fair_exists(
                self._fair_repository,
                operation.organization_id,
                source_fair_id,
            )

        if customer_id is not None:
            if self._customer_repository is None:
                raise InvalidOperationConfigError(
                    "Customer repository is required when linking customer_id"
                )
            try:
                ensure_customer_exists(
                    self._customer_repository,
                    operation.organization_id,
                    customer_id,
                )
            except InvalidTodoCustomerError as exc:
                raise InvalidOperationConfigError(str(exc)) from exc

        from datetime import UTC

        now = datetime.now(tz=UTC)

        todo = Todo.create(
            organization_id=operation.organization_id,
            title=title,
            created_by=context.user_id,
            description=str(description).strip() if description else None,
            status=TodoStatus.TODO,
            priority=priority,
            category=TodoCategory.GENEL_GOREV,
            deadline=due_at,
            assignee_user_id=assignee_user_id,
            customer_id=customer_id,
            source_fair_id=source_fair_id,
            now=now,
        )
        saved = self._todo_repository.add(todo)

        return HandlerStartResult(
            run_status=RunStatus.COMPLETED,
            total_items=0,
            message="Todo created for manual task",
            result_payload={"related_todo_id": str(saved.id)},
            related_todo_id=saved.id,
        )

    def on_cancel(
        self,
        *,
        operation: Operation,
        run=None,
        context: HandlerExecutionContext | None = None,
    ) -> None:
        # Preserve linked Todo history; Operation cancel does not delete/cancel Todo.
        _ = (operation, run, context)

    def on_retry(
        self,
        *,
        operation: Operation,
        run,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        _ = (operation, run, context)
        raise InvalidOperationConfigError("manual_task does not support retry")

    def _resolve_customer_id(self, operation: Operation) -> UUID | None:
        config = operation.type_config or {}
        customer_raw = config.get("customer_id")
        if customer_raw is None and isinstance(operation.source_config, dict):
            customer_raw = operation.source_config.get("customer_id")
        return _parse_optional_uuid(customer_raw)

    def _resolve_source_fair_id(self, operation: Operation) -> UUID | None:
        if operation.source_kind != SourceKind.FAIR:
            return None
        source_ids = extract_source_ids(operation.source_config)
        if not source_ids:
            return None
        if len(source_ids) > 1:
            raise InvalidOperationConfigError(
                "manual_task fair source supports at most one source_id"
            )
        return source_ids[0]
