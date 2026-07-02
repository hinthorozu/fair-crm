"""Customer delete cascade safety: hard delete vs archive."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel, ImportRowModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel


def _create_customer(client, auth_headers, name="Cascade Delete Customer"):
    response = client.post(
        "/api/v1/customers",
        json={"display_name": name, "status": "active"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_fair(client, auth_headers, name="Cascade Fair"):
    response = client.post(
        "/api/v1/fairs",
        json={"name": name, "status": "planned"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_contact(client, auth_headers, customer_id):
    response = client.post(
        "/api/v1/contacts",
        json={
            "customer_id": customer_id,
            "first_name": "Test",
            "last_name": "Contact",
            "is_primary": True,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_activity(client, auth_headers, customer_id, contact_id):
    response = client.post(
        "/api/v1/activities",
        json={
            "customer_id": customer_id,
            "contact_id": contact_id,
            "type": "call",
            "subject": "Cascade test activity",
            "activity_date": datetime.now(tz=UTC).isoformat(),
            "status": "open",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_participation(client, auth_headers, customer_id, fair_id, contact_id):
    response = client.post(
        "/api/v1/fair-participations",
        json={
            "customer_id": customer_id,
            "fair_id": fair_id,
            "primary_contact_id": contact_id,
            "hall": "A",
            "stand": "1",
            "participation_status": "exhibitor",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _count_for_customer(db_session, model, customer_id: str) -> int:
    return db_session.scalar(
        select(func.count())
        .select_from(model)
        .where(model.customer_id == UUID(customer_id))
    )


def _hard_delete_customer(db_session, customer_id: str) -> None:
    customer = db_session.get(CustomerModel, UUID(customer_id))
    assert customer is not None
    db_session.delete(customer)
    db_session.commit()
    db_session.expire_all()


def _seed_import_row_with_links(
    db_session,
    *,
    organization_id: UUID,
    fair_id: str,
    customer_id: str,
    participation_id: str,
) -> tuple[UUID, UUID]:
    now = datetime.now(tz=UTC)
    batch_id = uuid4()
    row_id = uuid4()
    db_session.add(
        ImportBatchModel(
            id=batch_id,
            organization_id=organization_id,
            fair_id=UUID(fair_id),
            source_type="excel",
            file_name="cascade-test.xlsx",
            status="completed",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        ImportRowModel(
            id=row_id,
            batch_id=batch_id,
            organization_id=organization_id,
            row_number=1,
            raw_data_json={"company": "Test"},
            normalized_data_json={"company": "Test"},
            status="applied",
            match_customer_id=UUID(customer_id),
            created_customer_id=UUID(customer_id),
            updated_customer_id=UUID(customer_id),
            match_participation_id=UUID(participation_id),
            created_participation_id=UUID(participation_id),
            updated_participation_id=UUID(participation_id),
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()
    return batch_id, row_id


def test_hard_delete_customer_cascades_related_records(client, auth_headers, db_session):
    customer_id = _create_customer(client, auth_headers)
    fair_id = _create_fair(client, auth_headers)
    contact_id = _create_contact(client, auth_headers, customer_id)
    _create_activity(client, auth_headers, customer_id, contact_id)
    _create_participation(client, auth_headers, customer_id, fair_id, contact_id)

    assert _count_for_customer(db_session, ContactModel, customer_id) == 1
    assert _count_for_customer(db_session, ActivityModel, customer_id) == 1
    assert _count_for_customer(db_session, CustomerFairParticipationModel, customer_id) == 1

    _hard_delete_customer(db_session, customer_id)

    assert _count_for_customer(db_session, ContactModel, customer_id) == 0
    assert _count_for_customer(db_session, ActivityModel, customer_id) == 0
    assert _count_for_customer(db_session, CustomerFairParticipationModel, customer_id) == 0

    fair_response = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert fair_response.status_code == 200


def test_hard_delete_customer_nulls_import_row_links(
    client, auth_headers, db_session, organization_id
):
    customer_id = _create_customer(client, auth_headers)
    fair_id = _create_fair(client, auth_headers)
    contact_id = _create_contact(client, auth_headers, customer_id)
    participation_id = _create_participation(client, auth_headers, customer_id, fair_id, contact_id)
    batch_id, row_id = _seed_import_row_with_links(
        db_session,
        organization_id=organization_id,
        fair_id=fair_id,
        customer_id=customer_id,
        participation_id=participation_id,
    )

    _hard_delete_customer(db_session, customer_id)

    row = db_session.get(ImportRowModel, row_id)
    assert row is not None
    assert row.match_customer_id is None
    assert row.created_customer_id is None
    assert row.updated_customer_id is None
    assert row.match_participation_id is None
    assert row.created_participation_id is None
    assert row.updated_participation_id is None

    assert db_session.get(ImportBatchModel, batch_id) is not None
    assert db_session.get(FairModel, UUID(fair_id)) is not None


def test_archive_customer_preserves_related_records(client, auth_headers, db_session):
    customer_id = _create_customer(client, auth_headers)
    fair_id = _create_fair(client, auth_headers)
    contact_id = _create_contact(client, auth_headers, customer_id)
    _create_activity(client, auth_headers, customer_id, contact_id)
    _create_participation(client, auth_headers, customer_id, fair_id, contact_id)

    archive_response = client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    assert _count_for_customer(db_session, ContactModel, customer_id) == 1
    assert _count_for_customer(db_session, ActivityModel, customer_id) == 1
    assert _count_for_customer(db_session, CustomerFairParticipationModel, customer_id) == 1
    assert db_session.get(CustomerModel, UUID(customer_id)) is not None

    fair_response = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert fair_response.status_code == 200
