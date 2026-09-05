"""Sync Operation / OperationRun state from system data-operation runs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.value_objects import OperationStatus, RunStatus
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import (
    merge_result_payload,
)
from app.modules.operations.infrastructure.repositories.operation_repository import (
    SqlAlchemyOperationRepository,
)
from app.modules.operations.infrastructure.repositories.operation_run_repository import (
    SqlAlchemyOperationRunRepository,
)
from app.modules.system_admin.domain.data_operation_entities import DataOperationRun
from app.modules.system_admin.domain.data_operation_value_objects import (
    DataOperationRunResult,
    DataOperationRunStatus,
)


def extract_data_operation_run_id(run: OperationRun | None) -> UUID | None:
    if run is None:
        return None
    details = run.error_details or {}
    result = details.get("result")
    if not isinstance(result, dict):
        return None
    raw = result.get("data_operation_run_id")
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


def map_data_operation_status_to_run_status(
    status: str | DataOperationRunStatus,
    *,
    result: str | DataOperationRunResult | None = None,
) -> str | None:
    value = status.value if isinstance(status, DataOperationRunStatus) else str(status)
    if value in {
        DataOperationRunStatus.QUEUED.value,
        DataOperationRunStatus.RUNNING.value,
    }:
        return RunStatus.RUNNING if value == DataOperationRunStatus.RUNNING.value else RunStatus.QUEUED
    if value == DataOperationRunStatus.COMPLETED.value:
        result_value = (
            result.value if isinstance(result, DataOperationRunResult) else (str(result) if result else None)
        )
        if result_value == DataOperationRunResult.FAILED.value:
            return RunStatus.FAILED
        return RunStatus.COMPLETED
    if value == DataOperationRunStatus.FAILED.value:
        return RunStatus.FAILED
    if value == DataOperationRunStatus.CANCELLED.value:
        return RunStatus.CANCELLED
    return None


def apply_data_operation_to_run(
    run: OperationRun,
    data_run: DataOperationRun,
    *,
    now: datetime | None = None,
) -> None:
    stamp = now or datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "data_operation_run_id": str(data_run.id),
        "operation_key": data_run.operation_key,
        "data_operation_status": (
            data_run.status.value
            if isinstance(data_run.status, DataOperationRunStatus)
            else str(data_run.status)
        ),
        "data_operation_result": (
            data_run.result.value
            if isinstance(data_run.result, DataOperationRunResult)
            else data_run.result
        ),
    }
    if isinstance(data_run.summary_json, dict):
        payload["summary"] = data_run.summary_json
    if data_run.error_message:
        payload["warning_message"] = data_run.error_message
    merge_result_payload(run, payload)

    target = map_data_operation_status_to_run_status(data_run.status, result=data_run.result)
    if target is None:
        return

    if run.status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.PAUSED}:
        if target == RunStatus.RUNNING and run.status != RunStatus.RUNNING:
            run.transition_status(RunStatus.RUNNING, now=stamp)
        elif target == RunStatus.COMPLETED and run.status != RunStatus.COMPLETED:
            if run.status == RunStatus.QUEUED:
                run.transition_status(RunStatus.RUNNING, now=stamp)
            run.transition_status(RunStatus.COMPLETED, now=stamp)
            run.progress = 1.0
        elif target == RunStatus.FAILED and run.status != RunStatus.FAILED:
            run.mark_failed(
                now=stamp,
                error_code="data_operation_failed",
                error_message=data_run.error_message or "Data operation failed",
                error_details=dict(run.error_details or {}),
            )
        elif target == RunStatus.CANCELLED and run.status != RunStatus.CANCELLED:
            run.transition_status(RunStatus.CANCELLED, now=stamp)
        elif target == RunStatus.QUEUED and run.status == RunStatus.QUEUED:
            pass


def sync_operation_run_from_data_operation(
    db: Session,
    *,
    organization_id: UUID,
    operation_id: UUID,
    operation_run_id: UUID,
    data_run: DataOperationRun,
) -> None:
    now = datetime.now(tz=UTC)
    operation_repo = SqlAlchemyOperationRepository(db)
    run_repo = SqlAlchemyOperationRunRepository(db)

    operation = operation_repo.get_by_id(organization_id, operation_id)
    run = run_repo.get_by_id(organization_id, operation_run_id)
    if operation is None or run is None:
        return
    if run.operation_id != operation.id:
        return

    apply_data_operation_to_run(run, data_run, now=now)
    run_repo.update(run)
    _sync_operation_status(operation, run, now=now)
    operation_repo.update(operation)


def hydrate_run_from_data_operation(
    run: OperationRun,
    data_run: DataOperationRun,
) -> OperationRun:
    apply_data_operation_to_run(run, data_run)
    return run


def _sync_operation_status(
    operation: Operation,
    run: OperationRun,
    *,
    now: datetime,
) -> None:
    if run.status == RunStatus.COMPLETED:
        if operation.status == OperationStatus.ACTIVE:
            operation.transition_status(
                OperationStatus.COMPLETED, now=now, updated_by=operation.updated_by
            )
    elif run.status == RunStatus.FAILED:
        if operation.status not in {
            OperationStatus.ACTIVE,
            OperationStatus.READY,
            OperationStatus.CANCELLED,
            OperationStatus.ARCHIVED,
        }:
            return
    elif run.status == RunStatus.CANCELLED:
        if operation.status not in {
            OperationStatus.CANCELLED,
            OperationStatus.ARCHIVED,
            OperationStatus.COMPLETED,
        }:
            operation.transition_status(
                OperationStatus.CANCELLED, now=now, updated_by=operation.updated_by
            )
