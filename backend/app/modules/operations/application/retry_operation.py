from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort, AuditPort
from app.modules.operations.application.commands import OperationResult, RetryOperationCommand
from app.modules.operations.application.mappers import operation_to_result
from app.modules.operations.domain.entities import OperationRun
from app.modules.operations.domain.exceptions import (
    HandlerCapabilityNotSupportedError,
    HandlerNotRegisteredError,
    InvalidOperationConfigError,
    OperationNotFoundError,
    OperationRunNotFoundError,
)
from app.modules.operations.domain.handler import HandlerExecutionContext
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.ports import OperationRepository, OperationRunRepository
from app.modules.operations.domain.value_objects import OperationStatus, RunStatus

PERMISSION_EXECUTE = "fair_crm.operations.execute"


class RetryOperationUseCase:
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

    def execute(self, command: RetryOperationCommand) -> OperationResult:
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
        if not handler.capabilities.supports_retry:
            raise HandlerCapabilityNotSupportedError(
                f"{operation.operation_type} does not support retry"
            )

        run_id = command.run_id or operation.latest_run_id
        if run_id is None:
            raise OperationRunNotFoundError("No run available to retry")

        previous = self._run_repository.get_by_id(command.organization_id, run_id)
        if previous is None or previous.operation_id != operation.id:
            raise OperationRunNotFoundError("Operation run not found")
        if previous.status != RunStatus.FAILED:
            raise InvalidOperationConfigError("Only failed runs can be retried")

        now = datetime.now(tz=UTC)
        context = HandlerExecutionContext(
            user_id=command.user_id,
            access_token=command.access_token,
        )
        retry_run = OperationRun.create(
            organization_id=operation.organization_id,
            operation_id=operation.id,
            now=now,
            triggered_by=command.user_id,
            attempt=previous.attempt + 1,
            status=RunStatus.QUEUED,
        )
        saved_run = self._run_repository.add(retry_run)
        start_result = handler.on_retry(
            operation=operation, run=saved_run, context=context
        )

        saved_run.total_items = start_result.total_items
        if start_result.run_status == RunStatus.RUNNING:
            saved_run.transition_status(RunStatus.RUNNING, now=now)
        elif start_result.run_status == RunStatus.COMPLETED:
            saved_run.transition_status(RunStatus.RUNNING, now=now)
            saved_run.transition_status(RunStatus.COMPLETED, now=now)
        elif start_result.run_status == RunStatus.FAILED:
            saved_run.mark_failed(
                now=now,
                error_code="handler_retry_failed",
                error_message=start_result.message or "Handler retry failed",
            )
        saved_run = self._run_repository.update(saved_run)

        if operation.status in {OperationStatus.CANCELLED, OperationStatus.READY}:
            operation.transition_status(
                OperationStatus.ACTIVE, now=now, updated_by=command.user_id
            )
        operation.mark_latest_run(saved_run.id, now=now, updated_by=command.user_id)
        saved = self._operation_repository.update(operation)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.operation.retried",
            resource_type="operation",
            resource_id=str(saved.id),
            new_values={"run_id": str(saved_run.id), "attempt": saved_run.attempt},
            metadata={"user_id": str(command.user_id)},
        )

        return operation_to_result(saved, handler=handler, latest_run=saved_run)
