"""Tests for single-customer contact enrichment API on customers router."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import app.modules.scraper.api.dependencies as scraper_dependencies
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _seed_customer(
    db_session,
    organization_id,
    *,
    display_name: str,
    website: str | None = None,
    email: str | None = None,
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
    if website:
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
    if email:
        db_session.add(
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                email=email,
                is_primary=True,
                created_at=now,
            )
        )
    db_session.commit()
    return customer


def test_get_customer_contact_enrichment_state_not_scanned(client, auth_headers, db_session, organization_id):
    customer = _seed_customer(
        db_session,
        organization_id,
        display_name="State View Co",
        website="https://state-view.test",
    )

    response = client.get(
        f"/api/v1/customers/{customer.id}/contact-enrichment-state",
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == str(customer.id)
    assert payload["status"] == CustomerEnrichmentScanStatus.NOT_SCANNED
    assert payload["can_run"] is True
    assert payload["website"] == "https://state-view.test"
    assert payload["has_crm_email"] is False
    assert payload["block_code"] is None


def test_get_customer_contact_enrichment_state_no_website(client, auth_headers, db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="No Website Co")

    response = client.get(
        f"/api/v1/customers/{customer.id}/contact-enrichment-state",
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["can_run"] is False
    assert payload["block_code"] == "no_website"
    assert "web sitesi olmadığı" in payload["block_message"]


def test_get_customer_contact_enrichment_state_allows_run_when_email_exists(
    client, auth_headers, db_session, organization_id
):
    customer = _seed_customer(
        db_session,
        organization_id,
        display_name="Has Email Co",
        website="https://has-email.test",
        email="info@has-email.test",
    )

    response = client.get(
        f"/api/v1/customers/{customer.id}/contact-enrichment-state",
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["can_run"] is True
    assert payload["block_code"] is None
    assert payload["has_crm_email"] is True


def test_get_customer_contact_enrichment_state_pending_merge(client, auth_headers, db_session, organization_id):
    customer = _seed_customer(
        db_session,
        organization_id,
        display_name="Pending Merge Co",
        website="https://pending.test",
    )
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerEnrichmentStateModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            website="https://pending.test",
            last_enrichment_run_id=None,
            last_email_scan_at=now,
            last_email_scan_status=CustomerEnrichmentScanStatus.PENDING_MERGE,
            last_email_found="found@pending.test",
            last_source_url="https://pending.test",
            last_error=None,
            retry_after=None,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/customers/{customer.id}/contact-enrichment-state",
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == CustomerEnrichmentScanStatus.PENDING_MERGE
    assert payload["can_run"] is False
    assert payload["block_code"] == "pending_merge"
    assert "import bekleyen" in (payload["block_message"] or "").lower()


def test_run_customer_contact_enrichment_rejects_no_website(client, auth_headers, db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Run No Website Co")

    response = client.post(
        f"/api/v1/customers/{customer.id}/contact-enrichment/run",
        json={"dry_run": True, "requested_fields": ["email"]},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "web sitesi olmadığı" in response.json()["detail"]


def test_run_customer_contact_enrichment_starts_when_email_exists(
    client, auth_headers, db_session, organization_id
):
    customer = _seed_customer(
        db_session,
        organization_id,
        display_name="Run Has Email Co",
        website="https://run-email.test",
        email="info@run-email.test",
    )
    captured_commands: list[EnrichmentRunJobCommand] = []

    def _capture_runner(session_factory, executor):
        runner = EnrichmentRunJobRunner(session_factory=session_factory, executor=executor)

        def _run_enrichment(command: EnrichmentRunJobCommand):
            captured_commands.append(command)
            return None

        runner.run_enrichment = _run_enrichment  # type: ignore[method-assign]
        return runner

    mock_runner = _capture_runner(lambda: db_session, lambda *args, **kwargs: ([], None))
    previous_runner = scraper_dependencies._enrichment_run_job_runner
    scraper_dependencies._enrichment_run_job_runner = mock_runner
    try:
        response = client.post(
            f"/api/v1/customers/{customer.id}/contact-enrichment/run",
            json={"dry_run": True, "requested_fields": ["email"]},
            headers=auth_headers,
        )
    finally:
        scraper_dependencies._enrichment_run_job_runner = previous_runner

    assert response.status_code == 202
    assert len(captured_commands) == 1
    assert captured_commands[0].customer_ids == [customer.id]


def test_run_customer_contact_enrichment_starts_for_eligible_customer(
    client, auth_headers, db_session, organization_id, user_id
):
    customer = _seed_customer(
        db_session,
        organization_id,
        display_name="Run Eligible Co",
        website="https://eligible.test",
    )
    captured_commands: list[EnrichmentRunJobCommand] = []

    def _capture_runner(session_factory, executor):
        runner = EnrichmentRunJobRunner(session_factory=session_factory, executor=executor)

        def _run_enrichment(command: EnrichmentRunJobCommand):
            captured_commands.append(command)
            return None

        runner.run_enrichment = _run_enrichment  # type: ignore[method-assign]
        return runner

    mock_runner = _capture_runner(lambda: db_session, lambda *args, **kwargs: ([], None))
    previous_runner = scraper_dependencies._enrichment_run_job_runner
    scraper_dependencies._enrichment_run_job_runner = mock_runner
    try:
        response = client.post(
            f"/api/v1/customers/{customer.id}/contact-enrichment/run",
            json={"dry_run": True, "requested_fields": ["email", "phone"]},
            headers=auth_headers,
        )
    finally:
        scraper_dependencies._enrichment_run_job_runner = previous_runner

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["adapter_key"] == ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT
    assert len(captured_commands) == 1
    command = captured_commands[0]
    assert command.customer_ids == [customer.id]
    assert command.limit == 1
    assert command.dry_run is True
    assert command.requested_fields == ["email", "phone"]


def test_reset_enrichment_state_preserves_crm_email(client, auth_headers, db_session, organization_id):
    customer = _seed_customer(
        db_session,
        organization_id,
        display_name="Reset Preserve Email Co",
        website="https://preserve.test",
        email="keep@preserve.test",
    )
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerEnrichmentStateModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            website="https://preserve.test",
            last_enrichment_run_id=None,
            last_email_scan_at=now,
            last_email_scan_status=CustomerEnrichmentScanStatus.EMAIL_FOUND,
            last_email_found="found@preserve.test",
            last_source_url="https://preserve.test",
            last_error=None,
            retry_after=None,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    reset_response = client.post(
        "/api/v1/scraper/enrichment-state/reset",
        json={"customer_ids": [str(customer.id)]},
        headers=auth_headers,
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["deleted_count"] == 1

    state_response = client.get(
        f"/api/v1/customers/{customer.id}/contact-enrichment-state",
        headers=auth_headers,
    )
    assert state_response.status_code == 200
    state_payload = state_response.json()
    assert state_payload["status"] == CustomerEnrichmentScanStatus.NOT_SCANNED
    assert state_payload["has_crm_email"] is True
    assert state_payload["can_run"] is True
    assert state_payload["block_code"] is None

    email_count = (
        db_session.query(CustomerEmailModel)
        .filter(
            CustomerEmailModel.organization_id == organization_id,
            CustomerEmailModel.customer_id == customer.id,
        )
        .count()
    )
    assert email_count == 1
