from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort, AuditPort
from app.modules.operations.application.commands import OperationResult, StartOperationCommand
from app.modules.operations.application.mappers import operation_to_result
from app.modules.operations.domain.entities import OperationRun
from app.modules.operations.domain.exceptions import (
    HandlerNotRegisteredError,
    InvalidOperationConfigError,
    OperationNotFoundError,
)
from app.modules.operations.domain.handler import HandlerExecutionContext
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.ports import OperationRepository, OperationRunRepository
from app.modules.operations.domain.value_objects import OperationStatus, OperationType, RunStatus

PERMISSION_EXECUTE = "fair_crm.operations.execute"


class StartOperationUseCase:
    def __init__(
        self,
        operation_repository: OperationRepository,
        run_repository: OperationRunRepository,
        handler_registry: InMemoryHandlerRegistry,
        authorization: AuthorizationPort,
        audit: AuditPort,
    ) -> None:
        self._operation_repository = operation_repository
        self._run_repository = run_repository
        self._handler_registry = handler_registry
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: StartOperationCommand) -> OperationResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_EXECUTE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        operation = self._operation_repository.get_by_id(
            command.organization_id, command.operation_id
        )
        if operation is None:
            raise OperationNotFoundError("Operation not found")

        handler = self._handler_registry.get(operation.operation_type)
        if handler is None:
            raise HandlerNotRegisteredError(
                f"No handler registered for operation type: {operation.operation_type}"
            )

        # Idempotent manual_task start: Todo already linked → return current state.
        if (
            operation.operation_type == OperationType.MANUAL_TASK
            and operation.related_todo_id is not None
        ):
            return operation_to_result(
                operation,
                handler=handler,
                latest_run=self._load_latest_run(operation),
            )

        validation = handler.validate_start(operation=operation)
        if not validation.ok:
            raise InvalidOperationConfigError("; ".join(validation.errors))

        now = datetime.now(tz=UTC)
        context = HandlerExecutionContext(
            user_id=command.user_id,
            access_token=command.access_token,
        )
        run = OperationRun.create(
            organization_id=operation.organization_id,
            operation_id=operation.id,
            now=now,
            triggered_by=command.user_id,
            status=RunStatus.QUEUED,
        )
        saved_run = self._run_repository.add(run)

        start_result = handler.on_start(
            operation=operation, run=saved_run, context=context
        )

        saved_run.total_items = start_result.total_items
        if start_result.result_payload:
            saved_run.error_details = {
                **saved_run.error_details,
                "result": start_result.result_payload,
            }
        if start_result.run_status == RunStatus.COMPLETED:
            if saved_run.status == RunStatus.QUEUED:
                saved_run.transition_status(RunStatus.RUNNING, now=now)
            saved_run.transition_status(RunStatus.COMPLETED, now=now)
        elif start_result.run_status == RunStatus.RUNNING:
            saved_run.transition_status(RunStatus.RUNNING, now=now)
        elif start_result.run_status == RunStatus.FAILED:
            saved_run.mark_failed(
                now=now,
                error_code="handler_start_failed",
                error_message=start_result.message or "Handler start failed",
                error_details=dict(saved_run.error_details or {}),
            )
        elif start_result.run_status != RunStatus.QUEUED:
            saved_run.transition_status(start_result.run_status, now=now)

        saved_run = self._run_repository.update(saved_run)

        if operation.status in {OperationStatus.DRAFT, OperationStatus.READY}:
            operation.transition_status(
                OperationStatus.ACTIVE, now=now, updated_by=command.user_id
            )

        # Manual task orchestration finishes when Todo is created (no background worker).
        if (
            operation.operation_type == OperationType.MANUAL_TASK
            and start_result.run_status == RunStatus.COMPLETED
            and operation.status == OperationStatus.ACTIVE
        ):
            operation.transition_status(
                OperationStatus.COMPLETED, now=now, updated_by=command.user_id
            )

        if start_result.related_todo_id is not None and operation.related_todo_id is None:
            operation.link_related_todo(
                start_result.related_todo_id,
                now=now,
                updated_by=command.user_id,
            )

        operation.mark_latest_run(saved_run.id, now=now, updated_by=command.user_id)
        saved_operation = self._operation_repository.update(operation)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.operation.started",
            resource_type="operation",
            resource_id=str(saved_operation.id),
            new_values={
                "run_id": str(saved_run.id),
                "run_status": saved_run.status,
                "related_todo_id": (
                    str(saved_operation.related_todo_id)
                    if saved_operation.related_todo_id
                    else None
                ),
            },
            metadata={"user_id": str(command.user_id)},
        )

        return operation_to_result(
            saved_operation, handler=handler, latest_run=saved_run
        )

    def _load_latest_run(self, operation):
        if operation.latest_run_id is None:
            return None
        return self._run_repository.get_by_id(
            operation.organization_id, operation.latest_run_id
        )
