"""Tests for POST /api/v1/fairs/{fair_id}/run."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import app.modules.fairs.api.dependencies as fairs_dependencies
from app.modules.scraper.application.fair_scraper_job_runner import FairScraperJobCommand, FairScraperJobRunner
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _sample_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[{"company_name": "Demo Co", "website": "", "email": "", "phone": ""}],
        row_metadata=[{}],
    )


def _mock_scrape_executor(**_kwargs) -> ScraperImportHandoff:
    return _sample_handoff()


def test_run_fair_scraper_starts_run_and_completes_with_mock(
    client, auth_headers, db_session, organization_id, user_id
):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Run Test Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
            "scraper_config": {"use_http": True},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = create_response.json()["id"]

    mock_runner = FairScraperJobRunner(session_factory=lambda: db_session, scrape_executor=_mock_scrape_executor)
    previous_runner = fairs_dependencies._fair_scraper_job_runner
    fairs_dependencies._fair_scraper_job_runner = mock_runner
    try:
        response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
    finally:
        fairs_dependencies._fair_scraper_job_runner = previous_runner

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["adapter_key"] == ScraperSiteKey.TUYAP_NEW
    assert payload["input_url"] == "https://foodist.test/brands"
    assert payload["fair_id"] == fair_id
    assert payload["fair_name"] == "Run Test Fair"
    assert payload["organization_id"] == str(organization_id)

    run_id = UUID(payload["id"])
    mock_runner.run_fair_scraper(
        FairScraperJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            fair_id=UUID(fair_id),
            user_id=user_id,
        )
    )
    db_session.expire_all()

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    completed = service.get_run(run_id)
    assert completed is not None
    assert completed.status.value == "completed"
    assert completed.total_rows == 1
    assert completed.output_json_path is not None
    assert completed.run_source.value == "fair_automation"
    assert completed.import_batch_id is not None

    batch_response = client.get(f"/api/v1/imports/{completed.import_batch_id}", headers=auth_headers)
    assert batch_response.status_code == 200
    assert batch_response.json()["status"] == "decision_required"
    assert batch_response.json()["source_type"] == "scraper"

    logs_response = client.get(f"/api/v1/scraper/runs/{run_id}/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    assert len(logs_response.json()["items"]) >= 1


def test_run_fair_scraper_respects_adapter_output_formats(
    client, auth_headers, db_session, organization_id, user_id
):
    client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
        json={"output": {"json_handoff": True, "excel": False}},
        headers=auth_headers,
    )

    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Output Format Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = create_response.json()["id"]

    mock_runner = FairScraperJobRunner(session_factory=lambda: db_session, scrape_executor=_mock_scrape_executor)
    response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
    assert response.status_code == 202
    run_id = UUID(response.json()["id"])

    mock_runner.run_fair_scraper(
        FairScraperJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            fair_id=UUID(fair_id),
            user_id=user_id,
        )
    )
    db_session.expire_all()

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    completed = service.get_run(run_id)
    assert completed is not None
    assert completed.status.value == "completed"
    assert completed.output_json_path is not None
    assert completed.output_excel_path is None
    assert completed.import_batch_id is not None

    logs_response = client.get(f"/api/v1/scraper/runs/{run_id}/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    logs_payload = logs_response.json()
    assert logs_payload["output_json_available"] is True
    assert logs_payload["output_excel_available"] is False


def test_run_fair_scraper_produces_excel_when_manifest_enabled(
    client, auth_headers, db_session, organization_id, user_id
):
    client.patch(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
        json={"output": {"json_handoff": False, "excel": True}},
        headers=auth_headers,
    )

    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Excel Only Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = create_response.json()["id"]

    mock_runner = FairScraperJobRunner(session_factory=lambda: db_session, scrape_executor=_mock_scrape_executor)
    response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
    assert response.status_code == 202
    run_id = UUID(response.json()["id"])

    mock_runner.run_fair_scraper(
        FairScraperJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            fair_id=UUID(fair_id),
            user_id=user_id,
        )
    )
    db_session.expire_all()

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    completed = service.get_run(run_id)
    assert completed is not None
    assert completed.output_json_path is None
    assert completed.output_excel_path is not None
    assert completed.import_batch_id is not None

    logs_response = client.get(f"/api/v1/scraper/runs/{run_id}/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    logs_payload = logs_response.json()
    assert logs_payload["output_json_available"] is False
    assert logs_payload["output_excel_available"] is True

    excel_response = client.get(f"/api/v1/scraper/runs/{run_id}/output/excel", headers=auth_headers)
    assert excel_response.status_code == 200
    assert "spreadsheetml" in excel_response.headers["content-type"]


def test_run_fair_scraper_without_adapter_returns_400(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={"name": "No Adapter Fair"},
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]

    response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)

    assert response.status_code == 400
    assert "adapter" in response.json()["detail"].lower()
    assert "adapter" in response.json()["detail"].lower()


def test_run_fair_scraper_without_source_url_rejected_on_create(client, auth_headers):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "No URL Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 400


def test_run_fair_scraper_not_found(client, auth_headers):
    response = client.post(
        f"/api/v1/fairs/{uuid4()}/run",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_run_fair_scraper_returns_503_when_playwright_browser_missing(client, auth_headers, monkeypatch):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Missing Browser Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = create_response.json()["id"]

    monkeypatch.setattr(
        "app.modules.scraper.core.playwright_availability.is_playwright_browser_installed",
        lambda config=None: False,
    )
    response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Playwright browser kurulu değil. Local için: python -m playwright install"
    )


def test_list_scraper_runs_filter_by_fair_id(client, auth_headers, db_session, organization_id):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Filter Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/list",
        },
        headers=auth_headers,
    )
    fair_id = UUID(create_response.json()["id"])
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://foodist.test/list",
        fair_name="Filter Fair",
        fair_year=2026,
        handoff=_sample_handoff(),
        organization_id=organization_id,
        fair_id=fair_id,
    )
    db_session.flush()

    response = client.get(f"/api/v1/scraper/runs?fair_id={fair_id}", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["fair_id"] == str(fair_id)
