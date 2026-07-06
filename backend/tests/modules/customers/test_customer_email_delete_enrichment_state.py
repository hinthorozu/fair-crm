"""Enrichment state behavior when customer emails are removed or updated."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel


def _seed_customer_with_communications(
    db_session,
    organization_id,
    *,
    display_name: str,
    emails: list[str],
    phone: str = "0212 555 0101",
    website: str = "https://example.test",
) -> CustomerModel:
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
    db_session.add(
        CustomerPhoneModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            phone=phone,
            is_primary=True,
            created_at=now,
        )
    )
    db_session.add(
        CustomerWebsiteModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            website=website,
            is_primary=True,
            created_at=now,
        )
    )
    for index, email in enumerate(emails):
        db_session.add(
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                email=email,
                is_primary=index == 0,
                created_at=now,
            )
        )
    db_session.commit()
    return customer


def _seed_enrichment_state(db_session, organization_id, customer_id, *, status: str) -> None:
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerEnrichmentStateModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            website="https://example.test",
            last_enrichment_run_id=None,
            last_email_scan_at=now,
            last_email_scan_status=status,
            last_email_found="found@example.test",
            last_source_url="https://example.test/contact",
            last_error=None,
            retry_after=None,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()


def _state_count(db_session, organization_id, customer_id) -> int:
    return (
        db_session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id == customer_id,
        )
        .count()
    )


def test_delete_last_email_resets_enrichment_state(client, auth_headers, db_session, organization_id):
    customer = _seed_customer_with_communications(
        db_session,
        organization_id,
        display_name="Single Email Co",
        emails=["only@example.test"],
    )
    _seed_enrichment_state(
        db_session,
        organization_id,
        customer.id,
        status=CustomerEnrichmentScanStatus.EMAIL_FOUND,
    )
    assert _state_count(db_session, organization_id, customer.id) == 1

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={"emails": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["emails"] == []
    assert _state_count(db_session, organization_id, customer.id) == 0


def test_delete_one_of_many_emails_preserves_enrichment_state(
    client, auth_headers, db_session, organization_id
):
    customer = _seed_customer_with_communications(
        db_session,
        organization_id,
        display_name="Multi Email Co",
        emails=[
            "one@example.test",
            "two@example.test",
            "three@example.test",
            "four@example.test",
        ],
    )
    _seed_enrichment_state(
        db_session,
        organization_id,
        customer.id,
        status=CustomerEnrichmentScanStatus.PENDING_MERGE,
    )

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={
            "emails": [
                {"email": "one@example.test", "is_primary": True},
                {"email": "three@example.test", "is_primary": False},
                {"email": "four@example.test", "is_primary": False},
            ]
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["emails"]) == 3
    assert _state_count(db_session, organization_id, customer.id) == 1
    state = (
        db_session.query(CustomerEnrichmentStateModel)
        .filter(CustomerEnrichmentStateModel.customer_id == customer.id)
        .one()
    )
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.PENDING_MERGE


def test_update_email_value_preserves_enrichment_state(client, auth_headers, db_session, organization_id):
    customer = _seed_customer_with_communications(
        db_session,
        organization_id,
        display_name="Update Email Co",
        emails=["old@example.test"],
    )
    _seed_enrichment_state(
        db_session,
        organization_id,
        customer.id,
        status=CustomerEnrichmentScanStatus.SKIPPED_EMAIL_EXISTS,
    )

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={"emails": [{"email": "new@example.test", "is_primary": True}]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["emails"][0]["email"] == "new@example.test"
    assert _state_count(db_session, organization_id, customer.id) == 1


def test_email_delete_reset_does_not_remove_other_crm_communications(
    client, auth_headers, db_session, organization_id
):
    customer = _seed_customer_with_communications(
        db_session,
        organization_id,
        display_name="Preserve Comm Co",
        emails=["remove@example.test"],
        phone="905551234567",
        website="https://preserve.test",
    )
    _seed_enrichment_state(
        db_session,
        organization_id,
        customer.id,
        status=CustomerEnrichmentScanStatus.EMAIL_FOUND,
    )

    response = client.patch(
        f"/api/v1/customers/{customer.id}",
        json={"emails": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert _state_count(db_session, organization_id, customer.id) == 0

    phone_count = (
        db_session.query(CustomerPhoneModel)
        .filter(CustomerPhoneModel.customer_id == customer.id)
        .count()
    )
    website_count = (
        db_session.query(CustomerWebsiteModel)
        .filter(CustomerWebsiteModel.customer_id == customer.id)
        .count()
    )
    assert phone_count == 1
    assert website_count == 1


def test_email_delete_reset_only_affects_target_customer(client, auth_headers, db_session, organization_id):
    target = _seed_customer_with_communications(
        db_session,
        organization_id,
        display_name="Target Co",
        emails=["target@example.test"],
    )
    other = _seed_customer_with_communications(
        db_session,
        organization_id,
        display_name="Other Co",
        emails=["other@example.test"],
    )
    _seed_enrichment_state(
        db_session,
        organization_id,
        target.id,
        status=CustomerEnrichmentScanStatus.EMAIL_FOUND,
    )
    _seed_enrichment_state(
        db_session,
        organization_id,
        other.id,
        status=CustomerEnrichmentScanStatus.EMAIL_FOUND,
    )

    response = client.patch(
        f"/api/v1/customers/{target.id}",
        json={"emails": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert _state_count(db_session, organization_id, target.id) == 0
    assert _state_count(db_session, organization_id, other.id) == 1
