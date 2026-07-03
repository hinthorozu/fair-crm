from datetime import UTC, datetime
from uuid import uuid4

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.application.customer_merge_reassignment import (
    mark_loser_customers_deleted,
    reassign_loser_customer_relationships,
)
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel, ImportRowModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel


def _seed_customer(db_session, organization_id, *, display_name: str) -> CustomerModel:
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=display_name,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def test_reassign_loser_customer_relationships_moves_all_related_rows(db_session, organization_id):
    now = datetime.now(tz=UTC)
    survivor = _seed_customer(db_session, organization_id, display_name="Survivor Co")
    loser = _seed_customer(db_session, organization_id, display_name="Loser Co")

    contact = ContactModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=loser.id,
        first_name="Ada",
        last_name="Lovelace",
        is_primary=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    activity = ActivityModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=loser.id,
        activity_type="call",
        subject="Follow up",
        activity_date=now,
        status="completed",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    batch = ImportBatchModel(
        id=uuid4(),
        organization_id=organization_id,
        file_name="import.xlsx",
        status="completed",
        created_at=now,
        updated_at=now,
    )
    import_row = ImportRowModel(
        id=uuid4(),
        batch_id=batch.id,
        organization_id=organization_id,
        row_number=1,
        raw_data_json={},
        normalized_data_json={},
        status="applied",
        match_customer_id=loser.id,
        created_customer_id=loser.id,
        updated_customer_id=loser.id,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([contact, activity, batch, import_row])
    db_session.flush()

    reassign_loser_customer_relationships(
        db_session,
        organization_id=organization_id,
        survivor_id=survivor.id,
        loser_ids=[loser.id],
        now=now,
    )
    mark_loser_customers_deleted(
        db_session,
        organization_id=organization_id,
        loser_ids=[loser.id],
        now=now,
    )
    db_session.flush()

    db_session.refresh(contact)
    db_session.refresh(activity)
    db_session.refresh(import_row)
    db_session.refresh(loser)

    assert contact.customer_id == survivor.id
    assert activity.customer_id == survivor.id
    assert import_row.match_customer_id == survivor.id
    assert import_row.created_customer_id == survivor.id
    assert import_row.updated_customer_id == survivor.id
    assert loser.deleted_at is not None
    assert loser.status == CustomerStatus.DELETED.value

    assert (
        db_session.query(CustomerFairParticipationModel)
        .filter(CustomerFairParticipationModel.customer_id == loser.id)
        .count()
        == 0
    )


def test_reassign_participations_with_autoflush_disabled_soft_deletes_before_bulk_move(
    test_engine, organization_id
):
    """Production sessions use autoflush=False; soft-deletes must flush before bulk update."""
    from sqlalchemy.orm import sessionmaker

    from app.modules.fairs.infrastructure.persistence.models import FairModel

    now = datetime.now(tz=UTC)
    Session = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = Session()
    survivor = _seed_customer(session, organization_id, display_name="Survivor Co")
    loser = _seed_customer(session, organization_id, display_name="Loser Co")
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Sample Fair",
        normalized_name="sample fair",
        status="active",
        created_at=now,
        updated_at=now,
    )
    session.add(fair)
    session.flush()
    session.add_all(
        [
            CustomerFairParticipationModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=survivor.id,
                fair_id=fair.id,
                participation_status="exhibitor",
                created_at=now,
                updated_at=now,
            ),
            CustomerFairParticipationModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=loser.id,
                fair_id=fair.id,
                participation_status="exhibitor",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    session.flush()

    reassign_loser_customer_relationships(
        session,
        organization_id=organization_id,
        survivor_id=survivor.id,
        loser_ids=[loser.id],
        now=now,
    )
    session.flush()

    active_count = (
        session.query(CustomerFairParticipationModel)
        .filter(
            CustomerFairParticipationModel.customer_id == survivor.id,
            CustomerFairParticipationModel.deleted_at.is_(None),
        )
        .count()
    )
    assert active_count == 1
    session.close()


def test_reassign_participations_dedupes_active_fair_and_preserves_soft_deleted_history(
    db_session, organization_id
):
    from app.modules.fairs.infrastructure.persistence.models import FairModel

    now = datetime.now(tz=UTC)
    survivor = _seed_customer(db_session, organization_id, display_name="Survivor Co")
    loser = _seed_customer(db_session, organization_id, display_name="Loser Co")
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Sample Fair",
        normalized_name="sample fair",
        status="active",
        created_at=now,
        updated_at=now,
    )
    other_fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Other Fair",
        normalized_name="other fair",
        status="active",
        created_at=now,
        updated_at=now,
    )
    survivor_participation = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=survivor.id,
        fair_id=fair.id,
        participation_status="exhibitor",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    duplicate_active = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=loser.id,
        fair_id=fair.id,
        participation_status="exhibitor",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    unique_active = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=loser.id,
        fair_id=other_fair.id,
        participation_status="visitor",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([fair, other_fair, survivor_participation, duplicate_active, unique_active])
    db_session.flush()

    reassign_loser_customer_relationships(
        db_session,
        organization_id=organization_id,
        survivor_id=survivor.id,
        loser_ids=[loser.id],
        now=now,
    )
    db_session.flush()

    db_session.refresh(duplicate_active)
    db_session.refresh(unique_active)

    assert duplicate_active.deleted_at is not None
    assert duplicate_active.customer_id == survivor.id
    assert unique_active.deleted_at is None
    assert unique_active.customer_id == survivor.id
