"""Long-running single owner for every queued email delivery."""

from __future__ import annotations

import logging
import signal
import time

from app.core.logging import setup_logging
from app.db.session import SessionLocal
# The standalone worker does not import the FastAPI router tree. Register the
# table referenced by crm_operations.related_todo_id before ORM flushes.
from app.modules.todos.infrastructure.persistence import models as _todo_models  # noqa: F401
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    process_mail_send_operations,
)

logger = logging.getLogger(__name__)
_stop_requested = False


def _request_stop(_signum, _frame) -> None:
    global _stop_requested
    _stop_requested = True


def main() -> None:
    setup_logging()
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    logger.info("mail_worker_service_started")

    while not _stop_requested:
        session = SessionLocal()
        try:
            result = process_mail_send_operations(session)
            session.commit()
            if result.picked_count or result.retried_count or result.recovered_stuck_count:
                logger.info(
                    "mail_worker_cycle picked=%s sent=%s failed=%s retries_queued=%s recovered=%s",
                    result.picked_count,
                    result.sent_count,
                    result.failed_count,
                    result.retried_count,
                    result.recovered_stuck_count,
                )
            if result.picked_count == 0 and result.retried_count == 0:
                time.sleep(1)
        except Exception:
            session.rollback()
            logger.exception("mail_worker_cycle_failed")
            time.sleep(2)
        finally:
            session.close()

    logger.info("mail_worker_service_stopped")


if __name__ == "__main__":
    main()
