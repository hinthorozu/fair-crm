from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort, AuditPort
from app.modules.operations.application.commands import CancelOperationCommand, OperationResult
from app.modules.operations.application.mappers import operation_to_result
from app.modules.operations.domain.exceptions import (
    HandlerCapabilityNotSupportedError,
    HandlerNotRegisteredError,
    OperationNotFoundError,
    OperationRunNotFoundError,
)
from app.modules.operations.domain.handler import HandlerExecutionContext
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.ports import OperationRepository, OperationRunRepository
from app.modules.operations.domain.value_objects import OperationStatus, RunStatus

PERMISSION_EXECUTE = "fair_crm.operations.execute"


class CancelOperationUseCase:
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

    def execute(self, command: CancelOperationCommand) -> OperationResult:
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

        now = datetime.now(tz=UTC)
        context = HandlerExecutionContext(
            user_id=command.user_id,
            access_token=command.access_token,
        )
        run = None
        run_id = command.run_id or operation.latest_run_id
        if run_id is not None:
            run = self._run_repository.get_by_id(command.organization_id, run_id)
            if run is None:
                raise OperationRunNotFoundError("Operation run not found")
            if run.operation_id != operation.id:
                raise OperationRunNotFoundError("Operation run not found")
            if run.status not in {
                RunStatus.QUEUED,
                RunStatus.RUNNING,
                RunStatus.PAUSED,
                RunStatus.COMPLETED,
            }:
                raise HandlerCapabilityNotSupportedError(
                    f"Cannot cancel run in status {run.status}"
                )
            if run.status != RunStatus.COMPLETED:
                run.transition_status(RunStatus.CANCELLED, now=now)
                run = self._run_repository.update(run)

        handler.on_cancel(operation=operation, run=run, context=context)

        if operation.status not in {
            OperationStatus.CANCELLED,
            OperationStatus.ARCHIVED,
            OperationStatus.COMPLETED,
        }:
            operation.transition_status(
                OperationStatus.CANCELLED, now=now, updated_by=command.user_id
            )
        saved = self._operation_repository.update(operation)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.operation.cancelled",
            resource_type="operation",
            resource_id=str(saved.id),
            new_values={
                "status": saved.status,
                "related_todo_id": str(saved.related_todo_id) if saved.related_todo_id else None,
            },
            metadata={"user_id": str(command.user_id)},
        )

        return operation_to_result(saved, handler=handler, latest_run=run)
