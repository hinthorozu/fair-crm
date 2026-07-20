"""Startup recovery: drain queued mail_send_operations without blocking API boot."""

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


async def _startup_mail_recovery_task() -> None:
    try:
        await asyncio.to_thread(run_mail_queue_startup_recovery)
    except Exception:
        # Belt-and-suspenders: never let a recovery task crash the event loop.
        logger.exception("mail_queue_startup_recovery_task_failed")


def schedule_mail_queue_startup_recovery() -> asyncio.Task | None:
    """Schedule non-blocking recovery. Returns the task, or None when disabled."""
    settings = get_settings()
    if not settings.mail_startup_recovery_enabled:
        logger.info("mail_queue_startup_recovery_disabled")
        return None

    task = asyncio.create_task(_startup_mail_recovery_task())
    logger.info("mail_queue_startup_recovery_scheduled")
    return task
