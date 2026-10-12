from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

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


@pytest.mark.parametrize("origin", ["system", "organization"])
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("planned", "completed"),
        ("active", "completed"),
        ("cancelled", "cancelled"),
        ("archived", "archived"),
        ("completed", "completed"),
    ],
)
def test_expired_fair_status_matrix(db_session, origin, status, expected):
    today = date(2026, 10, 13)
    fair_id = _fair(
        db_session,
        origin=origin,
        status=status,
        end_date=today - timedelta(days=1),
    )
    original_updated_at = db_session.get(FairModel, fair_id).updated_at
    now = datetime(2026, 10, 12, 21, 30, tzinfo=UTC)

    assert complete_expired_fairs(db_session, today=today, now=now) == (
        1 if status in {"planned", "active"} else 0
    )
    db_session.expire_all()
    fair = db_session.get(FairModel, fair_id)
    assert fair.status == expected
    if status in {"planned", "active"}:
        assert fair.updated_at.replace(tzinfo=None) == now.replace(tzinfo=None)
    else:
        assert fair.updated_at == original_updated_at
    assert complete_expired_fairs(db_session, today=today, now=now) == 0


@pytest.mark.parametrize("origin", ["system", "organization"])
@pytest.mark.parametrize("end_date", [None, date(2026, 10, 13), date(2026, 10, 14)])
def test_not_expired_fairs_unchanged(db_session, origin, end_date):
    fair_id = _fair(db_session, origin=origin, status="planned", end_date=end_date)
    now = datetime(2026, 10, 12, 21, 30, tzinfo=UTC)
    assert complete_expired_fairs(db_session, today=date(2026, 10, 13), now=now) == 0
    db_session.expire_all()
    assert db_session.get(FairModel, fair_id).status == "planned"


@pytest.mark.parametrize("origin", ["system", "organization"])
def test_soft_deleted_expired_fair_unchanged(db_session, origin):
    fair_id = _fair(
        db_session, origin=origin, status="active", end_date=date(2026, 10, 12), deleted=True
    )
    now = datetime(2026, 10, 12, 21, 30, tzinfo=UTC)
    assert complete_expired_fairs(db_session, today=date(2026, 10, 13), now=now) == 0
    db_session.expire_all()
    assert db_session.get(FairModel, fair_id).status == "active"


def test_istanbul_calendar_boundary():
    assert datetime(2026, 10, 12, 20, 59, tzinfo=UTC).astimezone(ISTANBUL).date() == date(2026, 10, 12)
    assert datetime(2026, 10, 12, 21, 0, tzinfo=UTC).astimezone(ISTANBUL).date() == date(2026, 10, 13)
