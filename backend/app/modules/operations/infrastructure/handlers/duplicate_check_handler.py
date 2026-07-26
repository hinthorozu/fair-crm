"""Duplicate-check Operation handler — reuses system data-operation runners."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

from app.modules.customers.application.customer_field_grouping import GROUP_BY_FIELDS
from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.exceptions import InvalidOperationConfigError
from app.modules.operations.domain.handler import (
    HandlerExecutionContext,
    HandlerStartResult,
    HandlerValidationResult,
)
from app.modules.operations.domain.value_objects import (
    HandlerCapabilities,
    OperationType,
    RunStatus,
    SourceKind,
)
from app.modules.operations.infrastructure.handlers.duplicate_check_operation_sync import (
    extract_data_operation_run_id,
)
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import merge_result_payload
from app.modules.system_admin.application.data_operation_registry import (
    DATA_OPERATIONS_BY_KEY,
    get_operation_definition,
)

if TYPE_CHECKING:
    from app.modules.system_admin.application.data_operation_job_runner import DataOperationJobCommand
    from app.modules.system_admin.application.data_operation_service import RunDataOperationUseCase

VALID_JOB_KEYS = frozenset(DATA_OPERATIONS_BY_KEY.keys())
DUPLICATE_CUSTOMER_ANALYSIS_KEY = "duplicate_customer_analysis"


class DuplicateCheckHandler:
    """Starts Analyze / Duplicate Customer jobs via existing data-operation engine."""

    operation_type = OperationType.DUPLICATE_CHECK

    def __init__(
        self,
        *,
        run_data_operation_use_case: RunDataOperationUseCase | None = None,
        job_scheduler: Callable[[DataOperationJobCommand], None] | None = None,
    ) -> None:
        self._run_data_operation_use_case = run_data_operation_use_case
        self._job_scheduler = job_scheduler

    @property
    def capabilities(self) -> HandlerCapabilities:
        return HandlerCapabilities(
            supports_pause=False,
            supports_resume=False,
            supports_retry=True,
            supports_schedule=False,
            supports_items=True,
        )

    def validate_create(
        self,
        *,
        source_kind: str,
        source_config: dict[str, Any],
        type_config: dict[str, Any],
        run_settings: dict[str, Any],
        organization_id: UUID | None = None,
    ) -> HandlerValidationResult:
        _ = source_config, run_settings, organization_id
        errors: list[str] = []

        if source_kind not in {SourceKind.NONE, SourceKind.SEGMENT, SourceKind.MANUAL_SELECTION}:
            errors.append("duplicate_check requires source_kind=none (or segment/manual_selection)")

        job_key = str(type_config.get("job_key") or "").strip()
        if not job_key:
            errors.append("type_config.job_key is required")
        elif job_key not in VALID_JOB_KEYS:
            errors.append(
                "type_config.job_key must be one of: " + ", ".join(sorted(VALID_JOB_KEYS))
            )

        if job_key == DUPLICATE_CUSTOMER_ANALYSIS_KEY:
            group_by = str(type_config.get("group_by") or "").strip()
            if not group_by or group_by not in GROUP_BY_FIELDS:
                errors.append(
                    "type_config.group_by is required for duplicate_customer_analysis "
                    "(company_name, email, website, or phone)"
                )

        if errors:
            return HandlerValidationResult.failure(*errors)
        return HandlerValidationResult.success()

    def validate_start(self, *, operation: Operation) -> HandlerValidationResult:
        return self.validate_create(
            source_kind=operation.source_kind,
            source_config=operation.source_config,
            type_config=operation.type_config,
            run_settings=operation.run_settings,
            organization_id=operation.organization_id,
        )

    def on_start(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        return self._start_job(operation=operation, run=run, context=context)

    def on_retry(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        return self._start_job(operation=operation, run=run, context=context)

    def on_cancel(
        self,
        *,
        operation: Operation,
        run: OperationRun | None,
        context: HandlerExecutionContext | None = None,
    ) -> None:
        _ = operation, run, context
        return

    def _start_job(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        from app.modules.system_admin.application.data_operation_job_runner import (
            DataOperationJobCommand,
        )

        if self._run_data_operation_use_case is None:
            raise InvalidOperationConfigError(
                "Data operation use case is required to start duplicate_check operations"
            )
        if self._job_scheduler is None:
            raise InvalidOperationConfigError(
                "Background job scheduler is required for duplicate_check operations"
            )

        validation = self.validate_start(operation=operation)
        if not validation.ok:
            raise InvalidOperationConfigError("; ".join(validation.errors))

        type_config = dict(operation.type_config or {})
        job_key = str(type_config.get("job_key") or "").strip()
        group_by = str(type_config.get("group_by") or "").strip() or None
        definition = get_operation_definition(job_key)

        # Link an already-created data-operation run (UI may start the job then register Operation).
        existing_raw = type_config.get("data_operation_run_id")
        if existing_raw:
            try:
                existing_id = UUID(str(existing_raw))
            except (TypeError, ValueError) as exc:
                raise InvalidOperationConfigError(
                    "type_config.data_operation_run_id is invalid"
                ) from exc
            result_payload = {
                "data_operation_run_id": str(existing_id),
                "operation_key": job_key,
                "dataset_kind": definition.dataset_kind if definition else None,
                "result_mode": definition.result_mode if definition else None,
                "group_by": group_by,
            }
            merge_result_payload(run, result_payload)
            return HandlerStartResult(
                run_status=RunStatus.RUNNING,
                total_items=0,
                message="Linked existing data operation run",
                result_payload=result_payload,
            )

        try:
            data_run = self._run_data_operation_use_case.execute(
                organization_id=operation.organization_id,
                user_id=context.user_id,
                user_email=context.user_email,
                access_token=context.access_token,
                operation_key=job_key,
                group_by=group_by,
            )
        except Exception as exc:
            return HandlerStartResult(
                run_status=RunStatus.FAILED,
                total_items=0,
                message=str(exc) or "Data operation could not be started",
                result_payload={"operation_key": job_key},
            )

        result_payload = {
            "data_operation_run_id": str(data_run.id),
            "operation_key": data_run.operation_key,
            "dataset_kind": definition.dataset_kind if definition else None,
            "result_mode": definition.result_mode if definition else None,
            "group_by": group_by,
        }
        merge_result_payload(run, result_payload)

        self._job_scheduler(
            DataOperationJobCommand(
                organization_id=operation.organization_id,
                run_id=data_run.id,
                operation_id=operation.id,
                operation_run_id=run.id,
            )
        )

        return HandlerStartResult(
            run_status=RunStatus.RUNNING,
            total_items=0,
            message="Data operation started",
            result_payload=result_payload,
        )


# Keep extract helper import used by other modules via this package path if needed.
__all__ = ["DuplicateCheckHandler", "extract_data_operation_run_id"]
