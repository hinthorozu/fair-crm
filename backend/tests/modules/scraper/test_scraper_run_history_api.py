"""Tests for scraper run history API."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _sample_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[{"company_name": "Demo", "website": "https://demo.test", "email": "", "phone": ""}],
        row_metadata=[{"instagram_url": "https://instagram.com/demo"}],
    )


def test_list_scraper_runs_returns_recorded_runs(client: TestClient, db_session, auth_headers):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        handoff=_sample_handoff(),
        output_json_path="/tmp/handoff.json",
    )
    db_session.flush()

    response = client.get("/api/v1/scraper/runs", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["id"] == str(run.id)
    assert item["status"] == "completed"
    assert item["adapter_key"] == ScraperSiteKey.TUYAP_NEW
    assert item["total_rows"] == 1
    assert item["website_count"] == 1
    assert item["instagram_count"] == 1


def test_get_scraper_run_by_id(client: TestClient, db_session, auth_headers):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        error_message="timeout",
    )
    db_session.flush()

    response = client.get(f"/api/v1/scraper/runs/{run.id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["error_message"] == "timeout"
    assert payload["total_rows"] == 0


def test_get_scraper_run_not_found(client: TestClient, auth_headers):
    response = client.get(
        "/api/v1/scraper/runs/00000000-0000-0000-0000-000000000001",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_dashboard_summary_uses_run_history(client: TestClient, db_session):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_OLD,
        started_at=datetime.now(UTC),
        input_url="https://old.test",
        fair_name="Old",
        fair_year=2024,
        error_message="old failure",
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://new.test",
        fair_name="Foodist",
        fair_year=2026,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    response = client.get("/api/v1/scraper/dashboard")

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["last_run_adapter"] == ScraperSiteKey.TUYAP_NEW
    assert summary["failed_scraper_count"] == 1


def test_list_scraper_runs_filters_by_adapter_key(client: TestClient, db_session, auth_headers):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://new.test",
        fair_name="Foodist",
        fair_year=2026,
        handoff=_sample_handoff(),
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_OLD,
        started_at=datetime.now(UTC),
        input_url="https://old.test",
        fair_name="Old",
        fair_year=2024,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    response = client.get(
        "/api/v1/scraper/runs",
        params={"adapter_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["adapter_key"] == ScraperSiteKey.TUYAP_NEW


def test_list_scraper_runs_filters_by_status(client: TestClient, db_session, auth_headers):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://failed.test",
        fair_name="Foodist",
        fair_year=2026,
        error_message="timeout",
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://ok.test",
        fair_name="Foodist",
        fair_year=2026,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    response = client.get(
        "/api/v1/scraper/runs",
        params={"status": "failed"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["status"] == "failed"
