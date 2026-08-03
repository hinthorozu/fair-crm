"""Regression tests for live fair-email batch progress counters."""

from app.modules.fair_emails.infrastructure.persistence.models import (
    FairEmailBatchModel,
    FairEmailOutboxModel,
)
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)
from tests.modules.fair_emails.test_process_fair_email_batch import _seed_pending_batch


def test_outbox_terminal_updates_refresh_batch_progress(
    db_session,
    client,
    auth_headers,
    organization_id,
    user_id,
):
    batch_id = _seed_pending_batch(
        db_session,
        organization_id,
        user_id,
        client,
        auth_headers,
    )
    repository = SqlAlchemyFairEmailBatchRepository(db_session)
    outbox = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.batch_id == batch_id)
        .order_by(FairEmailOutboxModel.created_at.asc())
        .all()
    )

    repository.update_outbox_sent(
        outbox[0].id,
        subject="Test",
        body_html=None,
        body_text="Test",
    )
    db_session.flush()

    batch = (
        db_session.query(FairEmailBatchModel)
        .filter(FairEmailBatchModel.id == batch_id)
        .one()
    )
    assert batch.status == "processing"
    assert batch.sent_count == 1
    assert batch.failed_count == 0
    assert batch.completed_at is None

    repository.update_outbox_failed(outbox[1].id, message="Provider failure")
    db_session.flush()

    assert batch.status == "completed_with_errors"
    assert batch.sent_count == 1
    assert batch.failed_count == 1
    assert batch.completed_at is not None

    repository.prepare_outbox_for_retry(outbox[1].id)
    db_session.flush()

    assert batch.status == "processing"
    assert batch.sent_count == 1
    assert batch.failed_count == 0
    assert batch.completed_at is None
