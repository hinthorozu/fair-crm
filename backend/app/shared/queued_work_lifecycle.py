"""OL07-04 pre-start lifecycle enforcement for queued product work.

Only explicitly registered product background jobs are gated here.  A Core
lifecycle outage fails closed without terminalizing the queued record.  An
explicit non-active Core snapshot terminalizes the queued work so reactivation
cannot implicitly resume it.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.db.session import SessionLocal
from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)
from app.modules.data_integration.infrastructure.repositories.job_repository import (
    SqlAlchemyImportJobRepository,
)
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportJobStatus, ImportJobType
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
)
from app.modules.operations.infrastructure.handlers.duplicate_check_operation_sync import (
    sync_operation_run_from_data_operation,
)
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import (
    sync_operation_run_from_scraper,
)
from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.system_admin.domain.data_operation_value_objects import DataOperationRunStatus
from app.modules.system_admin.infrastructure.repositories.data_operation_run_repository import (
    SqlAlchemyDataOperationRunRepository,
)

logger = logging.getLogger(__name__)

_IMPORT_MODULE = "app.modules.data_integration.application.import_job_runner"
_SCRAPER_MODULES = {
    "app.modules.scraper.application.adapter_test_run_job_runner",
    "app.modules.scraper.application.fair_scraper_job_runner",
    "app.modules.scraper.application.enrichment_run_job_runner",
}
_DATA_OPERATION_MODULE = "app.modules.system_admin.application.data_operation_job_runner"

_ALLOWED_FUNCTIONS: dict[str, set[str]] = {
    _IMPORT_MODULE: {"run_analyze", "run_apply", "run_bulk_decision"},
    "app.modules.scraper.application.adapter_test_run_job_runner": {"run_adapter_test"},
    "app.modules.scraper.application.fair_scraper_job_runner": {"run_fair_scraper"},
    "app.modules.scraper.application.enrichment_run_job_runner": {"run_enrichment"},
    _DATA_OPERATION_MODULE: {
        "run_operation",
        "run_assign_customers_to_fair",
        "run_delete_selected_customers",
    },
}


@dataclass(frozen=True, slots=True)
class _QueuedWorkDescriptor:
    module: str
    function: str
    command: Any
    organization_id: UUID


def should_execute_queued_product_work(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> bool:
    """Return False when recognized queued product work must not start."""
    descriptor = _describe(func, args, kwargs)
    if descriptor is None:
        return True

    if not _is_locally_startable(descriptor):
        logger.info(
            "queued_product_work_not_startable module=%s function=%s organization_id=%s",
            descriptor.module,
            descriptor.function,
            descriptor.organization_id,
        )
        return False

    try:
        snapshot = OrganizationLifecycleGuard().get_snapshot(descriptor.organization_id)
    except OrganizationLifecycleUnavailableError:
        logger.warning(
            "queued_product_work_deferred_lifecycle_unavailable module=%s function=%s organization_id=%s",
            descriptor.module,
            descriptor.function,
            descriptor.organization_id,
        )
        return False

    if snapshot.work_allowed:
        return True

    reason = f"organization_lifecycle_prestart_cancelled:{snapshot.status}"
    try:
        _terminalize(descriptor, reason=reason)
    except Exception:
        # Cancellation persistence failure must never fall through to product work.
        logger.exception(
            "queued_product_work_cancellation_failed module=%s function=%s organization_id=%s",
            descriptor.module,
            descriptor.function,
            descriptor.organization_id,
        )
        return False

    logger.info(
        "queued_product_work_cancelled module=%s function=%s organization_id=%s lifecycle_status=%s",
        descriptor.module,
        descriptor.function,
        descriptor.organization_id,
        snapshot.status,
    )
    return False


def _describe(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> _QueuedWorkDescriptor | None:
    module = str(getattr(func, "__module__", ""))
    function = str(getattr(func, "__name__", ""))
    if function not in _ALLOWED_FUNCTIONS.get(module, set()):
        return None

    command = args[0] if args else kwargs.get("command")
    organization_id = getattr(command, "organization_id", None)
    if not isinstance(organization_id, UUID):
        logger.error(
            "queued_product_work_missing_organization module=%s function=%s",
            module,
            function,
        )
        # Recognized product work with malformed ownership metadata must fail closed.
        return _QueuedWorkDescriptor(
            module=module,
            function=function,
            command=command,
            organization_id=UUID(int=0),
        )
    return _QueuedWorkDescriptor(
        module=module,
        function=function,
        command=command,
        organization_id=organization_id,
    )


def _is_locally_startable(descriptor: _QueuedWorkDescriptor) -> bool:
    if descriptor.organization_id.int == 0:
        return False
    db = SessionLocal()
    try:
        if descriptor.module == _IMPORT_MODULE:
            job_id = getattr(descriptor.command, "job_id", None)
            if not isinstance(job_id, UUID):
                return False
            job = SqlAlchemyImportJobRepository(db).get_by_id(descriptor.organization_id, job_id)
            return job is not None and job.status == ImportJobStatus.QUEUED

        if descriptor.module == _DATA_OPERATION_MODULE:
            run_id = getattr(descriptor.command, "run_id", None)
            if not isinstance(run_id, UUID):
                return False
            run = SqlAlchemyDataOperationRunRepository(db).get_by_id(
                descriptor.organization_id,
                run_id,
            )
            return run is not None and run.status == DataOperationRunStatus.QUEUED

        if descriptor.module in _SCRAPER_MODULES:
            run_id = getattr(descriptor.command, "run_id", None)
            if not isinstance(run_id, UUID):
                return False
            run = create_run_history_service(db).get_run(
                run_id,
                organization_id=descriptor.organization_id,
            )
            # Scraper history is created as RUNNING before the background callback
            # is scheduled, so RUNNING is the local pre-start sentinel for this family.
            return run is not None and run.status == ScraperRunStatus.RUNNING

        return False
    finally:
        db.close()


def _terminalize(descriptor: _QueuedWorkDescriptor, *, reason: str) -> None:
    if descriptor.module == _IMPORT_MODULE:
        _terminalize_import(descriptor, reason=reason)
        return
    if descriptor.module == _DATA_OPERATION_MODULE:
        _terminalize_data_operation(descriptor, reason=reason)
        return
    if descriptor.module in _SCRAPER_MODULES:
        _terminalize_scraper(descriptor, reason=reason)
        return
    raise RuntimeError("Unsupported queued product work descriptor")


def _terminalize_import(descriptor: _QueuedWorkDescriptor, *, reason: str) -> None:
    db = SessionLocal()
    try:
        job_id = getattr(descriptor.command, "job_id", None)
        if not isinstance(job_id, UUID):
            return
        job_repo = SqlAlchemyImportJobRepository(db)
        job = job_repo.get_by_id(descriptor.organization_id, job_id)
        if job is None or job.status != ImportJobStatus.QUEUED:
            return

        now = datetime.now(tz=UTC)
        job.mark_cancelled(error_message=reason, now=now)
        job_repo.update(job)

        batch_repo = SqlAlchemyImportBatchRepository(db)
        batch = batch_repo.get_by_id(descriptor.organization_id, job.batch_id)
        if (
            job.job_type == ImportJobType.ANALYZE
            and batch is not None
            and batch.status == ImportBatchStatus.ANALYSIS_QUEUED
        ):
            # ANALYSIS_FAILED is intentionally retryable; the cancelled job itself
            # remains terminal and can never be auto-resumed after reactivation.
            batch.mark_analysis_failed(now=now, notes=reason)
            batch_repo.update(batch)
        elif (
            job.job_type == ImportJobType.APPLY
            and batch is not None
            and batch.status == ImportBatchStatus.APPLYING
        ):
            # StartImportApplyJob marks the batch APPLYING before the queued runner
            # starts. Pre-start lifecycle cancellation must not leave that batch
            # looking active after its queued job has been terminalized.
            batch.mark_cancelled(now=now, notes=reason)
            batch_repo.update(batch)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _terminalize_data_operation(descriptor: _QueuedWorkDescriptor, *, reason: str) -> None:
    db = SessionLocal()
    try:
        run_id = getattr(descriptor.command, "run_id", None)
        if not isinstance(run_id, UUID):
            return
        repo = SqlAlchemyDataOperationRunRepository(db)
        run = repo.get_by_id(descriptor.organization_id, run_id)
        if run is None or run.status != DataOperationRunStatus.QUEUED:
            return

        run.mark_cancelled(error_message=reason, now=datetime.now(tz=UTC))
        run = repo.update(run)

        operation_id = getattr(descriptor.command, "operation_id", None)
        operation_run_id = getattr(descriptor.command, "operation_run_id", None)
        if isinstance(operation_id, UUID) and isinstance(operation_run_id, UUID):
            sync_operation_run_from_data_operation(
                db,
                organization_id=descriptor.organization_id,
                operation_id=operation_id,
                operation_run_id=operation_run_id,
                data_run=run,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _terminalize_scraper(descriptor: _QueuedWorkDescriptor, *, reason: str) -> None:
    db = SessionLocal()
    try:
        run_id = getattr(descriptor.command, "run_id", None)
        if not isinstance(run_id, UUID):
            return
        history = create_run_history_service(db)
        # cancel_run re-reads the row and transitions only a still-RUNNING record.
        # This prevents a narrow pre-start race from rewriting an already terminal
        # scraper run (for example COMPLETED) to CANCELLED.
        cancelled = history.cancel_run(
            run_id,
            reason=reason,
            organization_id=descriptor.organization_id,
        )
        if cancelled is None or cancelled.status != ScraperRunStatus.CANCELLED:
            return

        operation_id = getattr(descriptor.command, "operation_id", None)
        operation_run_id = getattr(descriptor.command, "operation_run_id", None)
        if isinstance(operation_id, UUID) and isinstance(operation_run_id, UUID):
            sync_operation_run_from_scraper(
                db,
                organization_id=descriptor.organization_id,
                operation_id=operation_id,
                operation_run_id=operation_run_id,
                scraper_run=cancelled,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
