"""Tests for enrichment state reset API."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel


def test_reset_enrichment_state_by_customer_ids(client, auth_headers, db_session, organization_id):
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Reset API Co",
        normalized_name="reset api co",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        CustomerEnrichmentStateModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            website="https://x.test",
            last_enrichment_run_id=None,
            last_email_scan_at=now,
            last_email_scan_status=CustomerEnrichmentScanStatus.EMAIL_FOUND,
            last_email_found="a@x.test",
            last_source_url="https://x.test",
            last_error=None,
            retry_after=None,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/scraper/enrichment-state/reset",
        json={"customer_ids": [str(customer.id)]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1


def test_reset_enrichment_state_reset_all(client, auth_headers, db_session, organization_id):
    now = datetime.now(tz=UTC)
    customers = []
    for index in range(2):
        customer = CustomerModel(
            id=uuid4(),
            organization_id=organization_id,
            display_name=f"Reset All Co {index}",
            normalized_name=f"reset all co {index}",
            customer_type=CustomerType.LEAD.value,
            status=CustomerStatus.ACTIVE.value,
            source="manual",
            created_at=now,
            updated_at=now,
        )
        customers.append(customer)
        db_session.add(customer)
    db_session.flush()
    for customer in customers:
        db_session.add(
            CustomerEnrichmentStateModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website="https://all.test",
                last_enrichment_run_id=None,
                last_email_scan_at=now,
                last_email_scan_status=CustomerEnrichmentScanStatus.EMAIL_NOT_FOUND,
                last_email_found=None,
                last_source_url="https://all.test",
                last_error=None,
                retry_after=now,
                created_at=now,
                updated_at=now,
            )
        )
    db_session.commit()

    response = client.post(
        "/api/v1/scraper/enrichment-state/reset",
        json={"reset_all": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
