"""Tests for adapter test run API."""

from uuid import UUID

import app.modules.scraper.api.dependencies as scraper_dependencies
from app.modules.scraper.application.adapter_test_run_job_runner import (
    AdapterTestRunJobCommand,
    AdapterTestRunJobRunner,
)
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


def test_run_adapter_test_starts_run_and_streams_logs(client, auth_headers, db_session, organization_id):
    mock_runner = AdapterTestRunJobRunner(session_factory=lambda: db_session, scrape_executor=_mock_scrape_executor)
    previous_runner = scraper_dependencies._adapter_test_run_job_runner
    scraper_dependencies._adapter_test_run_job_runner = mock_runner
    try:
        response = client.post(
            f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/test-run",
            json={"input_url": "https://foodist.test/brands"},
            headers=auth_headers,
        )
    finally:
        scraper_dependencies._adapter_test_run_job_runner = previous_runner

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["adapter_key"] == ScraperSiteKey.TUYAP_NEW
    assert payload["input_url"] == "https://foodist.test/brands"
    assert payload["fair_id"] is None
    assert payload["organization_id"] == str(organization_id)

    run_id = UUID(payload["id"])
    mock_runner.run_adapter_test(
        AdapterTestRunJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            adapter_key=ScraperSiteKey.TUYAP_NEW,
            input_url="https://foodist.test/brands",
            output_json=True,
            output_excel=True,
        )
    )
    db_session.expire_all()

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    completed = service.get_run(run_id)
    assert completed is not None
    assert completed.status.value == "completed"
    assert completed.total_rows == 1
    assert completed.output_json_path is not None
    assert completed.output_excel_path is not None

    logs_response = client.get(f"/api/v1/scraper/runs/{run_id}/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    logs_payload = logs_response.json()
    assert len(logs_payload["items"]) >= 1
    assert logs_payload["total_rows"] == 1
    assert logs_payload["output_json_available"] is True
    assert logs_payload["output_excel_available"] is True

    json_response = client.get(f"/api/v1/scraper/runs/{run_id}/output/json", headers=auth_headers)
    assert json_response.status_code == 200
    assert json_response.headers["content-type"].startswith("application/json")

    excel_response = client.get(f"/api/v1/scraper/runs/{run_id}/output/excel", headers=auth_headers)
    assert excel_response.status_code == 200
    assert "spreadsheetml" in excel_response.headers["content-type"]


def test_run_adapter_test_rejects_invalid_url(client, auth_headers):
    response = client.post(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/test-run",
        json={"input_url": "not-a-url"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_run_adapter_test_rejects_invalid_max_pages(client, auth_headers):
    response = client.post(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/test-run",
        json={"input_url": "https://foodist.test/brands", "max_pages": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_run_adapter_test_passes_max_pages_to_job_runner(client, auth_headers, db_session, organization_id):
    captured: dict[str, object] = {}

    def _capturing_executor(**kwargs) -> ScraperImportHandoff:
        captured["context"] = kwargs.get("context")
        return _sample_handoff()

    mock_runner = AdapterTestRunJobRunner(
        session_factory=lambda: db_session,
        scrape_executor=_capturing_executor,
    )
    previous_runner = scraper_dependencies._adapter_test_run_job_runner
    scraper_dependencies._adapter_test_run_job_runner = mock_runner
    try:
        response = client.post(
            f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/test-run",
            json={"input_url": "https://foodist.test/brands", "max_pages": 3},
            headers=auth_headers,
        )
    finally:
        scraper_dependencies._adapter_test_run_job_runner = previous_runner

    assert response.status_code == 202
    run_id = UUID(response.json()["id"])
    mock_runner.run_adapter_test(
        AdapterTestRunJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            adapter_key=ScraperSiteKey.TUYAP_NEW,
            input_url="https://foodist.test/brands",
            output_json=True,
            output_excel=False,
            max_pages=3,
        )
    )

    context = captured.get("context")
    assert context is not None
    assert context.options.get("max_pages") == 3


def test_run_adapter_test_unknown_adapter(client, auth_headers):
    response = client.post(
        "/api/v1/scraper/adapters/unknown_adapter/test-run",
        json={"input_url": "https://example.test/list"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_run_adapter_test_returns_503_when_playwright_browser_missing(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.modules.scraper.core.playwright_availability.is_playwright_browser_installed",
        lambda config=None: False,
    )
    response = client.post(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/test-run",
        json={"input_url": "https://foodist.test/brands"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Playwright browser kurulu değil. Local için: python -m playwright install"
    )
