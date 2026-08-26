"""P0.1 tenant-isolation tests for fair-email batch/outbox repository mutations."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm.exc import NoResultFound

from app.modules.fair_emails.infrastructure.persistence.models import (
    FairEmailBatchModel,
    FairEmailOutboxModel,
)
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)


def _seed_batch(db_session, organization_id):
    now = datetime.now(timezone.utc)
    batch = FairEmailBatchModel(
        id=uuid4(),
        organization_id=organization_id,
        fair_id=None,
        operation_id=None,
        template_id=uuid4(),
        email_account_id=uuid4(),
        subject_override="Tenant isolation",
        recipient_options_json={},
        status="queued",
        total_count=1,
        sent_count=0,
        failed_count=0,
        skipped_count=0,
        created_by_user_id=uuid4(),
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    db_session.add(batch)
    outbox = FairEmailOutboxModel(
        id=uuid4(),
        batch_id=batch.id,
        organization_id=organization_id,
        customer_id=None,
        contact_id=None,
        participation_id=None,
        recipient_name="Tenant Test",
        company_name="Tenant Test",
        email="tenant-test@example.com",
        source="manual",
        status="queued",
        subject="Tenant isolation",
        email_account_id=batch.email_account_id,
        template_id=batch.template_id,
        fair_id=None,
        operation_logs=[],
        metadata_json={},
        created_at=now,
        updated_at=now,
    )
    db_session.add(outbox)
    db_session.commit()
    return batch, outbox


def test_foreign_organization_cannot_mutate_batch_or_outbox(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    batch, outbox = _seed_batch(db_session, owner_org)
    repository = SqlAlchemyFairEmailBatchRepository(db_session)

    with pytest.raises(NoResultFound):
        repository.mark_batch_processing(foreign_org, batch.id)

    with pytest.raises(NoResultFound):
        repository.mark_outbox_sending(foreign_org, batch.id, outbox.id)

    with pytest.raises(NoResultFound):
        repository.update_outbox_sent(
            foreign_org,
            batch.id,
            outbox.id,
            subject="foreign mutation",
            body_html=None,
            body_text="foreign mutation",
        )

    db_session.expire_all()
    stored_batch = db_session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch.id).one()
    stored_outbox = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox.id).one()
    assert stored_batch.status == "queued"
    assert stored_outbox.status == "queued"
    assert stored_outbox.sent_at is None


def test_own_organization_cannot_mutate_outbox_through_wrong_batch(db_session):
    organization_id = uuid4()
    first_batch, _ = _seed_batch(db_session, organization_id)
    second_batch, second_outbox = _seed_batch(db_session, organization_id)
    repository = SqlAlchemyFairEmailBatchRepository(db_session)

    with pytest.raises(NoResultFound):
        repository.update_outbox_failed(
            organization_id,
            first_batch.id,
            second_outbox.id,
            message="cross-linked mutation",
        )

    with pytest.raises(NoResultFound):
        repository.prepare_outbox_for_retry(
            organization_id,
            first_batch.id,
            second_outbox.id,
        )

    db_session.expire_all()
    stored = (
        db_session.query(FairEmailOutboxModel)
        .filter(FairEmailOutboxModel.id == second_outbox.id)
        .one()
    )
    assert stored.batch_id == second_batch.id
    assert stored.status == "queued"
    assert stored.error_message is None


def test_foreign_organization_bulk_child_queries_are_empty(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    batch, outbox = _seed_batch(db_session, owner_org)
    repository = SqlAlchemyFairEmailBatchRepository(db_session)

    assert repository.list_pending_outbox(foreign_org, batch.id) == []
    assert repository.list_failed_outbox(foreign_org, batch.id) == []
    assert repository.fail_all_pending_outbox(
        foreign_org,
        batch.id,
        message="foreign failure",
    ) == 0

    db_session.expire_all()
    stored = db_session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox.id).one()
    assert stored.status == "queued"
    assert stored.error_message is None
