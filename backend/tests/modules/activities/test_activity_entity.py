from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.exceptions import (
    InvalidActivitySubjectError,
    InvalidActivityTypeError,
)


def test_activity_create_with_defaults():
    now = datetime.now(tz=UTC)
    org_id = uuid4()
    customer_id = uuid4()

    activity = Activity.create(
        organization_id=org_id,
        customer_id=customer_id,
        activity_type="call",
        subject="Follow-up call",
        activity_date=now,
        status="open",
        now=now,
    )

    assert activity.subject == "Follow-up call"
    assert activity.source == "manual"
    assert activity.is_active is True
    assert activity.deleted_at is None


def test_activity_subject_required():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidActivitySubjectError):
        Activity.create(
            organization_id=uuid4(),
            customer_id=uuid4(),
            activity_type="call",
            subject="   ",
            activity_date=now,
            status="open",
            now=now,
        )


def test_activity_invalid_type():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidActivityTypeError):
        Activity.create(
            organization_id=uuid4(),
            customer_id=uuid4(),
            activity_type="invalid",
            subject="Test",
            activity_date=now,
            status="open",
            now=now,
        )


def test_activity_soft_delete():
    now = datetime.now(tz=UTC)
    activity = Activity.create(
        organization_id=uuid4(),
        customer_id=uuid4(),
        activity_type="note",
        subject="Note",
        activity_date=now,
        status="open",
        now=now,
    )
    activity.soft_delete(now=now)
    assert activity.deleted_at is not None
    assert activity.is_active is False
