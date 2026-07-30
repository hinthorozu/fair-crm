"""Live progress reporting for enrichment runs onto scraper history + operation run."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.operations.domain.value_objects import RunStatus
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import (
    merge_result_payload,
)
from app.modules.operations.infrastructure.repositories.operation_run_repository import (
    SqlAlchemyOperationRunRepository,
)
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service

logger = logging.getLogger(__name__)

EnrichmentProgressCallback = Callable[[int, int, int, int], None]


def enrichment_success_fail_counts(results: list[EnrichmentResultDto]) -> tuple[int, int]:
    """Split completed customers into succeeded (found) vs failed (everything else)."""
    succeeded = sum(1 for result in results if result.status == "found")
    failed = len(results) - succeeded
    return succeeded, failed


def report_enrichment_progress(
    session_factory: Callable[[], Session],
    *,
    run_id: UUID,
    organization_id: UUID,
    operation_id: UUID | None,
    operation_run_id: UUID | None,
    processed: int,
    total: int,
    succeeded: int,
    failed: int,
) -> None:
    """Persist live enrichment counters for UI polling (fresh session, commit)."""
    session = session_factory()
    try:
        history_service = create_run_history_service(session)
        history_service.touch_heartbeat(
            run_id,
            progress_current=processed,
            progress_total=total,
        )

        if operation_id is not None and operation_run_id is not None:
            run_repo = SqlAlchemyOperationRunRepository(session)
            run = run_repo.get_by_id(organization_id, operation_run_id)
            if run is not None and run.operation_id == operation_id:
                now = datetime.now(tz=UTC)
                if run.status == RunStatus.QUEUED:
                    run.transition_status(RunStatus.RUNNING, now=now)
                run.update_progress(
                    now=now,
                    total_items=total,
                    processed_items=processed,
                    succeeded_items=succeeded,
                    failed_items=failed,
                )
                merge_result_payload(
                    run,
                    {
                        "scraper_run_id": str(run_id),
                        "enrichment_progress": {
                            "total": total,
                            "processed": processed,
                            "succeeded": succeeded,
                            "failed": failed,
                        },
                    },
                )
                run_repo.update(run)

        session.commit()
    except Exception:
        logger.exception(
            "Failed to report enrichment progress run_id=%s processed=%s/%s",
            run_id,
            processed,
            total,
        )
        try:
            session.rollback()
        except Exception:
            logger.exception("Failed to rollback enrichment progress session run_id=%s", run_id)
    finally:
        session.close()
