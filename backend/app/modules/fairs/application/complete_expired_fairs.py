"""Daily persistence of expired Fair statuses (system and organization)."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel

logger = logging.getLogger(__name__)
ISTANBUL = ZoneInfo("Europe/Istanbul")


def complete_expired_fairs(session: Session, *, today: date, now: datetime) -> int:
    """Atomically complete only eligible rows, without read-then-write races."""
    statement = (
        update(FairModel)
        .where(
            FairModel.origin.in_(("system", "organization")),
            FairModel.end_date.isnot(None),
            FairModel.end_date < today,
            FairModel.deleted_at.is_(None),
            FairModel.status.notin_(
                (FairStatus.CANCELLED.value, FairStatus.ARCHIVED.value, FairStatus.COMPLETED.value)
            ),
        )
        .values(status=FairStatus.COMPLETED.value, updated_at=now)
        .execution_options(synchronize_session=False)
    )
    return int(session.execute(statement).rowcount or 0)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    now = datetime.now(tz=UTC)
    today = now.astimezone(ISTANBUL).date()
    with SessionLocal() as session:
        try:
            changed = complete_expired_fairs(session, today=today, now=now)
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Daily fair completion failed (today=%s)", today)
            return 1
    logger.info("Daily fair completion succeeded: today=%s changed=%s", today, changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
