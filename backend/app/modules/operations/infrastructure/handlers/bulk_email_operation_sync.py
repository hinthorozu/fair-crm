"""Sync Operation / OperationRun state from fair email batch outcomes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    FairEmailBatchRecord,
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.value_objects import OperationStatus, RunStatus
from app.modules.operations.infrastructure.repositories.operation_repository import (
    SqlAlchemyOperationRepository,
)
from app.modules.operations.infrastructure.repositories.operation_run_repository import (
    SqlAlchemyOperationRunRepository,
)


def extract_batch_id(run: OperationRun | None) -> UUID | None:
    if run is None:
        return None
    details = run.error_details or {}
    result = details.get("result")
    if not isinstance(result, dict):
        return None
    raw = result.get("batch_id")
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


def merge_result_payload(run: OperationRun, payload: dict[str, Any]) -> None:
    details = dict(run.error_details or {})
    existing = details.get("result")
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(payload)
    details["result"] = merged
    run.error_details = details


def map_batch_status_to_run_status(status: str) -> str | None:
    value = (status or "").strip().lower()
    if value in {"queued", "processing"}:
        return RunStatus.RUNNING
    if value == "completed":
        return RunStatus.COMPLETED
    if value in {"completed_with_errors", "failed"}:
        return RunStatus.FAILED
    return None


def apply_batch_progress_to_run(
    run: OperationRun,
    batch: FairEmailBatchRecord,
    *,
    now: datetime | None = None,
) -> None:
    stamp = now or datetime.now(tz=UTC)
    processed = batch.sent_count + batch.failed_count
    run.update_progress(
        now=stamp,
        total_items=batch.total_count,
        processed_items=min(processed, batch.total_count),
        succeeded_items=batch.sent_count,
        failed_items=batch.failed_count,
    )
    payload: dict[str, Any] = {
        "batch_id": str(batch.id),
        "batch_status": batch.status,
        "total_count": batch.total_count,
        "sent_count": batch.sent_count,
        "failed_count": batch.failed_count,
        "skipped_count": batch.skipped_count,
        "fair_id": str(batch.fair_id) if batch.fair_id else None,
    }
    merge_result_payload(run, payload)


def sync_operation_run_from_batch(
    db: Session,
    *,
    organization_id: UUID,
    operation_id: UUID,
    batch: FairEmailBatchRecord,
    operation_run_id: UUID | None = None,
) -> None:
    """Persist OperationRun/Operation terminal state from a fair email batch."""
    now = datetime.now(tz=UTC)
    operation_repo = SqlAlchemyOperationRepository(db)
    run_repo = SqlAlchemyOperationRunRepository(db)

    operation = operation_repo.get_by_id(organization_id, operation_id)
    if operation is None:
        return

    run = None
    if operation_run_id is not None:
        run = run_repo.get_by_id(organization_id, operation_run_id)
    if run is None and operation.latest_run_id is not None:
        run = run_repo.get_by_id(organization_id, operation.latest_run_id)
    if run is None or run.operation_id != operation.id:
        return

    apply_batch_progress_to_run(run, batch, now=now)
    target = map_batch_status_to_run_status(batch.status)
    if target is None:
        run_repo.update(run)
        return

    if run.status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.PAUSED}:
        if target == RunStatus.RUNNING and run.status != RunStatus.RUNNING:
            run.transition_status(RunStatus.RUNNING, now=now)
        elif target == RunStatus.COMPLETED and run.status != RunStatus.COMPLETED:
            if run.status == RunStatus.QUEUED:
                run.transition_status(RunStatus.RUNNING, now=now)
            run.transition_status(RunStatus.COMPLETED, now=now)
            run.progress = 1.0
        elif target == RunStatus.FAILED and run.status != RunStatus.FAILED:
            run.mark_failed(
                now=now,
                error_code="bulk_email_failed",
                error_message=(
                    f"Bulk email completed with errors "
                    f"(sent={batch.sent_count}, failed={batch.failed_count})"
                    if batch.sent_count > 0
                    else "Bulk email batch failed"
                ),
                error_details=dict(run.error_details or {}),
            )

    run_repo.update(run)
    _sync_operation_status(operation, run, now=now)
    operation_repo.update(operation)


def hydrate_run_from_batch(run: OperationRun, batch: FairEmailBatchRecord) -> OperationRun:
    """In-memory projection for read APIs (does not persist)."""
    apply_batch_progress_to_run(run, batch)
    target = map_batch_status_to_run_status(batch.status)
    if target and run.status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.PAUSED}:
        if target == RunStatus.COMPLETED:
            run.status = RunStatus.COMPLETED
            run.progress = 1.0
        elif target == RunStatus.FAILED:
            run.status = RunStatus.FAILED
            run.error_code = run.error_code or "bulk_email_failed"
        elif target == RunStatus.RUNNING and run.status == RunStatus.QUEUED:
            run.status = RunStatus.RUNNING
    return run


def resolve_batch_for_operation(
    db: Session,
    *,
    organization_id: UUID,
    operation_id: UUID,
    run: OperationRun | None = None,
) -> FairEmailBatchRecord | None:
    repo = SqlAlchemyFairEmailBatchRepository(db)
    batch = repo.get_batch_by_operation_id(organization_id, operation_id)
    if batch is not None:
        return batch
    batch_id = extract_batch_id(run)
    if batch_id is None:
        return None
    return repo.get_batch(organization_id, batch_id)


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
        # Keep operation active/ready so retry can continue.
        if operation.status not in {
            OperationStatus.ACTIVE,
            OperationStatus.READY,
            OperationStatus.CANCELLED,
            OperationStatus.ARCHIVED,
        }:
            return
    elif run.status == RunStatus.RUNNING and operation.status in {
        OperationStatus.DRAFT,
        OperationStatus.READY,
    }:
        operation.transition_status(
            OperationStatus.ACTIVE, now=now, updated_by=operation.updated_by
        )
