"""Tests for customer contact enrichment run API."""

from uuid import UUID

import app.modules.scraper.api.dependencies as scraper_dependencies
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.services.enrichment_run_summary_loader import load_enrichment_summary_for_run
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _sample_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[{"company_name": "Demo Co", "email": "info@demo.test"}],
        row_metadata=[{"external_id": "00000000-0000-0000-0000-000000000001"}],
    )


def _mock_executor(_session, _organization_id, **kwargs):
    customer_id = UUID("00000000-0000-0000-0000-000000000001")
    results = [
        EnrichmentResultDto(
            customer_id=customer_id,
            company_name="Demo Co",
            website="https://demo.test",
            emails=[SourcedValue(value="info@demo.test", source_url="https://demo.test/iletisim")],
            status="found",
        ),
        EnrichmentResultDto(
            customer_id=UUID("00000000-0000-0000-0000-000000000002"),
            company_name="Empty Co",
            website="https://empty.test",
            status="not_found",
        ),
    ]
    return results, _sample_handoff()


def test_enrichment_run_starts_and_completes_with_summary(
    client, auth_headers, db_session, organization_id, user_id
):
    mock_runner = EnrichmentRunJobRunner(session_factory=lambda: db_session, executor=_mock_executor)
    previous_runner = scraper_dependencies._enrichment_run_job_runner
    scraper_dependencies._enrichment_run_job_runner = mock_runner
    try:
        response = client.post(
            f"/api/v1/scraper/adapters/{ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT}/enrichment-run",
            json={"limit": 10, "dry_run": True, "requested_fields": ["email"]},
            headers=auth_headers,
        )
    finally:
        scraper_dependencies._enrichment_run_job_runner = previous_runner

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["adapter_key"] == ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT
    assert payload["fair_id"] is None
    assert payload["run_source"] == "enrichment"

    run_id = UUID(payload["id"])
    mock_runner.run_enrichment(
        EnrichmentRunJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            user_id=user_id,
            limit=10,
            requested_fields=["email"],
            dry_run=True,
        )
    )
    db_session.expire_all()

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    completed = service.get_run(run_id)
    assert completed is not None
    assert completed.status.value == "completed"
    assert completed.import_batch_id is None

    summary = load_enrichment_summary_for_run(create_run_log_service(db_session), run_id)
    assert summary is not None
    assert summary["customers_scanned"] == 2
    assert summary["emails_found"] == 1
    assert summary["not_found"] == 1
    assert summary["dry_run"] is True
    assert summary["import_batch_created"] is False

    detail_response = client.get(f"/api/v1/scraper/runs/{run_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["enrichment_summary"]["customers_scanned"] == 2
    assert detail["enrichment_summary"]["emails_found"] == 1


def test_enrichment_run_rejects_non_enrichment_adapter(client, auth_headers):
    response = client.post(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/enrichment-run",
        json={"limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 404
