"""Sync Operation / OperationRun state from scraper_run_history outcomes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.value_objects import OperationStatus, RunStatus
from app.modules.operations.infrastructure.repositories.operation_repository import (
    SqlAlchemyOperationRepository,
)
from app.modules.operations.infrastructure.repositories.operation_run_repository import (
    SqlAlchemyOperationRunRepository,
)
from app.modules.scraper.domain.scraper_run_history import ScraperRunHistory, ScraperRunStatus


def extract_scraper_run_id(run: OperationRun | None) -> UUID | None:
    if run is None:
        return None
    details = run.error_details or {}
    result = details.get("result")
    if not isinstance(result, dict):
        return None
    raw = result.get("scraper_run_id")
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


def merge_result_payload(
    run: OperationRun,
    payload: dict[str, Any],
) -> None:
    details = dict(run.error_details or {})
    existing = details.get("result")
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(payload)
    details["result"] = merged
    run.error_details = details


def map_scraper_status_to_run_status(status: str | ScraperRunStatus) -> str | None:
    value = status.value if isinstance(status, ScraperRunStatus) else str(status)
    if value in {
        ScraperRunStatus.RUNNING.value,
        ScraperRunStatus.CANCEL_REQUESTED.value,
        ScraperRunStatus.CANCELLING.value,
    }:
        return RunStatus.RUNNING
    if value == ScraperRunStatus.COMPLETED.value:
        return RunStatus.COMPLETED
    if value == ScraperRunStatus.FAILED.value:
        return RunStatus.FAILED
    if value == ScraperRunStatus.CANCELLED.value:
        return RunStatus.CANCELLED
    return None


def apply_scraper_progress_to_run(
    run: OperationRun,
    scraper_run: ScraperRunHistory,
    *,
    now: datetime | None = None,
) -> None:
    stamp = now or datetime.now(tz=UTC)
    total = scraper_run.progress_total
    current = scraper_run.progress_current or 0
    if total is not None and total > 0:
        run.update_progress(
            now=stamp,
            total_items=total,
            processed_items=min(current, total),
            succeeded_items=min(current, total),
        )
    elif scraper_run.total_rows:
        run.update_progress(
            now=stamp,
            total_items=scraper_run.total_rows,
            processed_items=scraper_run.total_rows,
            succeeded_items=scraper_run.total_rows,
        )

    payload: dict[str, Any] = {
        "scraper_run_id": str(scraper_run.id),
        "adapter_key": scraper_run.adapter_key,
        "fair_id": str(scraper_run.fair_id) if scraper_run.fair_id else None,
        "total_rows": scraper_run.total_rows,
        "import_batch_id": (
            str(scraper_run.import_batch_id) if scraper_run.import_batch_id else None
        ),
        "input_url": scraper_run.input_url,
        "scraper_status": (
            scraper_run.status.value
            if isinstance(scraper_run.status, ScraperRunStatus)
            else str(scraper_run.status)
        ),
    }
    if scraper_run.error_message:
        payload["warning_message"] = scraper_run.error_message
    merge_result_payload(run, payload)


def sync_operation_run_from_scraper(
    db: Session,
    *,
    organization_id: UUID,
    operation_id: UUID,
    operation_run_id: UUID,
    scraper_run: ScraperRunHistory,
) -> None:
    """Persist OperationRun/Operation terminal state from a scraper history record."""
    now = datetime.now(tz=UTC)
    operation_repo = SqlAlchemyOperationRepository(db)
    run_repo = SqlAlchemyOperationRunRepository(db)

    operation = operation_repo.get_by_id(organization_id, operation_id)
    run = run_repo.get_by_id(organization_id, operation_run_id)
    if operation is None or run is None:
        return
    if run.operation_id != operation.id:
        return

    apply_scraper_progress_to_run(run, scraper_run, now=now)
    target = map_scraper_status_to_run_status(scraper_run.status)
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
            if scraper_run.total_rows:
                run.total_items = scraper_run.total_rows
                run.processed_items = scraper_run.total_rows
                run.succeeded_items = scraper_run.total_rows
        elif target == RunStatus.FAILED and run.status != RunStatus.FAILED:
            run.mark_failed(
                now=now,
                error_code="scraper_failed",
                error_message=scraper_run.error_message or "Scraper run failed",
                error_details=dict(run.error_details or {}),
            )
        elif target == RunStatus.CANCELLED and run.status != RunStatus.CANCELLED:
            run.transition_status(RunStatus.CANCELLED, now=now)

    run_repo.update(run)
    _sync_operation_status(operation, run, now=now)
    operation_repo.update(operation)


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
        # Keep operation active/ready so retry can continue from the same definition.
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
    elif run.status == RunStatus.RUNNING and operation.status in {
        OperationStatus.DRAFT,
        OperationStatus.READY,
    }:
        operation.transition_status(
            OperationStatus.ACTIVE, now=now, updated_by=operation.updated_by
        )


def hydrate_run_from_scraper_history(
    run: OperationRun,
    scraper_run: ScraperRunHistory,
) -> OperationRun:
    """In-memory projection for read APIs (does not persist)."""
    apply_scraper_progress_to_run(run, scraper_run)
    target = map_scraper_status_to_run_status(scraper_run.status)
    if target and run.status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.PAUSED}:
        if target == RunStatus.COMPLETED:
            run.status = RunStatus.COMPLETED
            run.progress = 1.0
            run.finished_at = scraper_run.finished_at or run.finished_at
        elif target == RunStatus.FAILED:
            run.status = RunStatus.FAILED
            run.error_code = run.error_code or "scraper_failed"
            run.error_message = scraper_run.error_message or run.error_message
            run.finished_at = scraper_run.finished_at or run.finished_at
        elif target == RunStatus.CANCELLED:
            run.status = RunStatus.CANCELLED
            run.finished_at = scraper_run.finished_at or run.finished_at
        elif target == RunStatus.RUNNING and run.status == RunStatus.QUEUED:
            run.status = RunStatus.RUNNING
            if run.started_at is None:
                run.started_at = scraper_run.started_at
    return run
