"""Tests for POST /api/v1/fairs/{fair_id}/contact-enrichment/run."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import app.modules.fairs.api.dependencies as fairs_dependencies
from app.modules.scraper.application.enrichment_run_job_runner import EnrichmentRunJobRunner
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.enrichment_run_executor import EnrichmentRunExecution
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import CustomerWebsiteModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel


def _seed_fair(db_session, organization_id, *, name: str = "Enrichment Fair") -> FairModel:
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name=name,
        normalized_name=name.lower(),
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()
    return fair


def _seed_customer(db_session, organization_id, *, name: str, website: str | None = None) -> CustomerModel:
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=name,
        normalized_name=name.lower(),
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
        db_session.flush()
    return customer


def _seed_participation(db_session, organization_id, fair_id, customer_id) -> CustomerFairParticipationModel:
    now = datetime.now(tz=UTC)
    participation = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer_id,
        fair_id=fair_id,
        participation_status="exhibitor",
        created_at=now,
        updated_at=now,
    )
    db_session.add(participation)
    db_session.flush()
    return participation


def _sample_handoff(customer_id: UUID) -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[{"company_name": "Fair Co", "email": "info@fair-co.test"}],
        row_metadata=[{"external_id": str(customer_id)}],
    )


def test_run_fair_contact_enrichment_starts_run_with_fair_id(
    client, auth_headers, db_session, organization_id, user_id
):
    fair = _seed_fair(db_session, organization_id)
    fair_customer = _seed_customer(
        db_session,
        organization_id,
        name="Fair Participant",
        website="https://fair-participant.test",
    )
    other_customer = _seed_customer(
        db_session,
        organization_id,
        name="Other Org Customer",
        website="https://other-org.test",
    )
    _seed_participation(db_session, organization_id, fair.id, fair_customer.id)
    db_session.commit()

    # Capture plain values before any request: the mock job runner closes/expunges
    # db_session synchronously (TestClient runs BackgroundTasks inline), which would
    # detach any ORM instances still referenced afterwards.
    fair_id = fair.id
    fair_name = fair.name
    fair_customer_id = fair_customer.id
    fair_customer_name = fair_customer.display_name
    other_customer_id = other_customer.id

    captured: dict[str, object] = {}

    def _mock_executor(_session, _organization_id, **kwargs):
        captured["fair_id"] = kwargs.get("fair_id")
        captured["customer_ids"] = kwargs.get("customer_ids")
        return EnrichmentRunExecution(
            results=[
                EnrichmentResultDto(
                    customer_id=fair_customer_id,
                    company_name=fair_customer_name,
                    website="https://fair-participant.test",
                    emails=[SourcedValue(value="info@fair-co.test", source_url="https://fair-participant.test")],
                    status="found",
                )
            ],
            handoff=_sample_handoff(fair_customer_id),
        )

    mock_runner = EnrichmentRunJobRunner(session_factory=lambda: db_session, executor=_mock_executor)
    previous_runner = fairs_dependencies._enrichment_run_job_runner
    fairs_dependencies._enrichment_run_job_runner = mock_runner
    try:
        response = client.post(
            f"/api/v1/fairs/{fair_id}/contact-enrichment/run",
            json={"limit": 10, "dry_run": False, "requested_fields": ["email"]},
            headers=auth_headers,
        )
    finally:
        fairs_dependencies._enrichment_run_job_runner = previous_runner

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["adapter_key"] == ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT
    assert payload["fair_id"] == str(fair_id)
    assert payload["fair_name"] == fair_name
    assert payload["run_source"] == "enrichment"

    run_id = UUID(payload["id"])
    assert captured["fair_id"] == fair_id
    assert captured["customer_ids"] is None

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    completed = service.get_run(run_id)
    assert completed is not None
    assert completed.status.value == "completed"
    assert completed.fair_id == fair_id
    assert completed.import_batch_id is not None

    batch_response = client.get(f"/api/v1/imports/{completed.import_batch_id}", headers=auth_headers)
    assert batch_response.status_code == 200
    assert batch_response.json()["fair_id"] == str(fair_id)

    # Other fair customer without participation must not affect candidate validation for this fair.
    assert other_customer_id != fair_customer_id


def test_run_fair_contact_enrichment_rejects_when_no_candidates(
    client, auth_headers, db_session, organization_id
):
    fair = _seed_fair(db_session, organization_id)
    customer = _seed_customer(
        db_session,
        organization_id,
        name="No Website Co",
        website=None,
    )
    _seed_participation(db_session, organization_id, fair.id, customer.id)
    db_session.commit()

    response = client.post(
        f"/api/v1/fairs/{fair.id}/contact-enrichment/run",
        json={"limit": 10},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "zenginleştirilecek müşteri bulunamadı" in response.json()["detail"]


def test_run_fair_contact_enrichment_not_found(client, auth_headers):
    response = client.post(
        f"/api/v1/fairs/{uuid4()}/contact-enrichment/run",
        json={"limit": 10},
        headers=auth_headers,
    )
    assert response.status_code == 404
