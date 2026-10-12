from datetime import UTC, date, datetime
from uuid import uuid4

from app.modules.fairs.application.complete_expired_fairs import (
    ISTANBUL,
    complete_expired_fairs,
)
from app.modules.fairs.infrastructure.persistence.models import FairModel


def _fair(session, *, origin, status, end_date, deleted=False):
    now = datetime(2026, 10, 12, 22, 0, tzinfo=UTC)
    model = FairModel(
        id=uuid4(),
        organization_id=uuid4() if origin == "organization" else None,
        origin=origin,
        name="Test fair",
        normalized_name="test fair",
        identity_name="test fair",
        status=status,
        start_date=None,
        end_date=end_date,
        deleted_at=now if deleted else None,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    session.flush()
    return model.id


def test_completion_covers_both_origins_and_preserves_exclusions(db_session):
    yesterday = date(2026, 10, 12)
    today = date(2026, 10, 13)
    cases = [
        ("system", "planned", yesterday, False, "completed"),
        ("organization", "active", yesterday, False, "completed"),
        ("organization", "planned", today, False, "planned"),
        ("system", "active", date(2026, 10, 14), False, "active"),
        ("system", "planned", None, False, "planned"),
        ("organization", "cancelled", yesterday, False, "cancelled"),
        ("system", "archived", yesterday, False, "archived"),
        ("organization", "active", yesterday, True, "active"),
        ("system", "completed", yesterday, False, "completed"),
    ]
    ids = [
        _fair(db_session, origin=origin, status=status, end_date=end, deleted=deleted)
        for origin, status, end, deleted, _ in cases
    ]
    now = datetime(2026, 10, 12, 21, 30, tzinfo=UTC)
    assert complete_expired_fairs(db_session, today=today, now=now) == 2
    db_session.expire_all()
    assert [db_session.get(FairModel, key).status for key in ids] == [case[4] for case in cases]
    assert complete_expired_fairs(db_session, today=today, now=now) == 0


def test_istanbul_calendar_boundary():
    assert datetime(2026, 10, 12, 20, 59, tzinfo=UTC).astimezone(ISTANBUL).date() == date(2026, 10, 12)
    assert datetime(2026, 10, 12, 21, 0, tzinfo=UTC).astimezone(ISTANBUL).date() == date(2026, 10, 13)
