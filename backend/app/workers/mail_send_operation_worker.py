"""CLI entry point for mail send operation worker (Phase 1)."""

from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.modules.mail_send_operations.application.process_mail_send_operations_worker import (
    process_mail_send_operations,
)

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    session = SessionLocal()
    try:
        result = process_mail_send_operations(session)
        session.commit()
        logger.info(
            "mail_worker_completed recovered=%s picked=%s sent=%s failed=%s skipped=%s",
            result.recovered_stuck_count,
            result.picked_count,
            result.sent_count,
            result.failed_count,
            result.skipped_count,
        )
    except Exception:
        session.rollback()
        logger.exception("mail_worker_failed")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
