"""Regression tests for live fair-email batch progress counters."""

from app.modules.fair_emails.infrastructure.persistence.models import (
    FairEmailBatchModel,
    FairEmailOutboxModel,
)
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)
from tests.modules.fair_emails.test_process_fair_email_batch import _seed_pending_batch


def test_chunk_progress_refreshes_batch_once_requested(
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
        external_message_id="provider-message-1",
        provider_status="accepted",
    )
    db_session.flush()

    db_session.refresh(outbox[0])
    assert outbox[0].external_message_id == "provider-message-1"
    assert outbox[0].provider_status == "accepted"
    assert outbox[0].error_code is None
    assert outbox[0].error_message is None

    sent_count, failed_count, status = repository.recount_batch_from_outbox(batch_id)
    repository.update_batch_counts(
        batch_id,
        status=status,
        sent_count=sent_count,
        failed_count=failed_count,
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

    sent_count, failed_count, status = repository.recount_batch_from_outbox(batch_id)
    repository.update_batch_counts(
        batch_id,
        status=status,
        sent_count=sent_count,
        failed_count=failed_count,
    )
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


def test_pending_outbox_iterator_loads_fixed_size_chunks(
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
    iterator = repository.iter_pending_outbox(batch_id, chunk_size=1)

    first = next(iterator)
    repository.update_outbox_sent(
        first.id,
        subject="Test",
        body_html=None,
        body_text="Test",
    )
    db_session.commit()

    second = next(iterator)
    assert second.id != first.id
