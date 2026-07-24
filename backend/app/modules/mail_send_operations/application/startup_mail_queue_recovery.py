"""Mail queue recovery: drain queued ops and re-check stuck ``sending`` while alive.

Immediate pass on app startup, then periodic re-evaluation so orphan ``sending``
rows past ``mail_sending_timeout_minutes`` become terminal FAILED even when
startup ran before the timeout elapsed. Never auto-retries or resends.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    MailSendOperationWorkerResult,
    process_mail_send_operations_background,
)
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    SqlAlchemyMailSendOperationRepository,
)

logger = logging.getLogger(__name__)


def count_startup_recovery_candidates() -> tuple[int, int]:
    """Return ``(queued_ready, stuck_sending_past_timeout)`` for the startup probe.

    Stuck ``sending`` rows are never re-queued here; they are only counted so the
    existing worker timeout recovery can mark them failed when a drain runs.
    """
    from app.db.session import SessionLocal
    from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
        _mail_worker_session_factory,
    )

    settings = get_settings()
    session_factory = _mail_worker_session_factory or SessionLocal
    session = session_factory()
    owns_session = _mail_worker_session_factory is None
    try:
        repository = SqlAlchemyMailSendOperationRepository(session)
        now = datetime.now(timezone.utc)
        queued = repository.count_queued_ready(now=now)
        stuck = repository.count_stuck_sending_past_timeout(
            cutoff=now - timedelta(minutes=settings.mail_sending_timeout_minutes),
        )
        return queued, stuck
    finally:
        if owns_session:
            session.close()


def count_pending_queued_mail_operations() -> int:
    """Backward-compatible alias: queued-ready count only."""
    queued, _stuck = count_startup_recovery_candidates()
    return queued


def run_mail_queue_startup_recovery() -> MailSendOperationWorkerResult | None:
    """Synchronously trigger the existing background drain worker.

    Intended to run on a worker thread (not the asyncio event loop / startup thread).
    Never raises to callers that need boot resilience — logs and returns None on failure.
    """
    logger.info("mail_queue_startup_recovery_started")
    try:
        queued, stuck = count_startup_recovery_candidates()
        if queued == 0 and stuck == 0:
            logger.info(
                "mail_queue_startup_recovery_empty pending_queued=0 stuck_sending=0",
            )
            return MailSendOperationWorkerResult(
                recovered_stuck_count=0,
                picked_count=0,
                sent_count=0,
                failed_count=0,
                skipped_count=0,
            )

        logger.info(
            "mail_queue_startup_recovery_triggering pending_queued=%s stuck_sending=%s",
            queued,
            stuck,
        )
        result = process_mail_send_operations_background()
        logger.info(
            "mail_queue_startup_recovery_completed recovered=%s picked=%s sent=%s failed=%s skipped=%s",
            result.recovered_stuck_count,
            result.picked_count,
            result.sent_count,
            result.failed_count,
            result.skipped_count,
        )
        return result
    except Exception:
        logger.exception("mail_queue_startup_recovery_failed")
        return None


def _stuck_sending_poll_seconds() -> int:
    """How often to re-evaluate stuck ``sending`` while the process is alive.

    Startup alone is not enough: if recovery runs before ``sending_timeout`` has
    elapsed, an orphan ``sending`` row would otherwise stay stuck forever. Keep
    the existing timeout semantics; only re-check on a short poll interval.
    """
    settings = get_settings()
    # Default 15m timeout → 60s poll; clamp so checks stay frequent but not frantic.
    return max(30, min(120, int(settings.mail_sending_timeout_minutes) * 4))


async def _mail_queue_recovery_supervisor() -> None:
    """Run startup drain immediately, then periodically while the app lives.

    Each pass reuses ``run_mail_queue_startup_recovery`` (stuck-sending timeout
    failure + queued drain). Does not resend, does not auto-retry.
    """
    poll_seconds = _stuck_sending_poll_seconds()
    logger.info(
        "mail_queue_recovery_supervisor_started poll_seconds=%s",
        poll_seconds,
    )
    while True:
        try:
            await asyncio.to_thread(run_mail_queue_startup_recovery)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Belt-and-suspenders: never let a recovery pass crash the event loop.
            logger.exception("mail_queue_startup_recovery_task_failed")
        try:
            await asyncio.sleep(poll_seconds)
        except asyncio.CancelledError:
            raise


def schedule_mail_queue_startup_recovery() -> asyncio.Task | None:
    """Schedule non-blocking recovery (+ periodic stuck-sending checks).

    Returns the supervisor task, or None when disabled.
    """
    settings = get_settings()
    if not settings.mail_startup_recovery_enabled:
        logger.info("mail_queue_startup_recovery_disabled")
        return None

    task = asyncio.create_task(_mail_queue_recovery_supervisor())
    logger.info("mail_queue_startup_recovery_scheduled")
    return task
