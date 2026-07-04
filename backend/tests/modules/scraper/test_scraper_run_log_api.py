"""Tests for scraper run console log API."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.modules.scraper.domain.scraper_run_log import ScraperRunLogLevel
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.infrastructure.repositories.scraper_run_log_repository import ScraperRunLogRepository
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _seed_run_with_logs(db_session):
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    logs = ScraperRunLogService(ScraperRunLogRepository(db_session))
    run = history.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        started_at=datetime.now(UTC),
    )
    first = logs.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.INFO,
        step="started",
        message="TÜYAP New adapter çalışıyor",
    )
    second = logs.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.SUCCESS,
        step="completed",
        message="490 kayıt tamamlandı",
        metadata={"total_rows": 490},
    )
    history.complete_run(
        run.id,
        handoff=ScraperImportHandoff(
            canonical_rows=[{"company_name": "Demo"}],
        ),
    )
    db_session.flush()
    return run, first, second


def test_list_run_logs_returns_ordered_items(client: TestClient, db_session):
    run, first, second = _seed_run_with_logs(db_session)

    response = client.get(f"/api/v1/scraper/runs/{run.id}/logs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["run_status"] == "completed"
    assert payload["items"][0]["id"] == str(first.id)
    assert payload["items"][1]["id"] == str(second.id)
    assert payload["items"][0]["step"] == "started"
    assert payload["items"][1]["level"] == "success"


def test_list_run_logs_supports_after_id(client: TestClient, db_session):
    run, first, _second = _seed_run_with_logs(db_session)

    response = client.get(f"/api/v1/scraper/runs/{run.id}/logs", params={"after_id": str(first.id)})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["step"] == "completed"


def test_list_run_logs_not_found_for_unknown_run(client: TestClient):
    response = client.get("/api/v1/scraper/runs/00000000-0000-0000-0000-000000000001/logs")

    assert response.status_code == 404


def test_failed_run_logs_include_error_level(client: TestClient, db_session):
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    logs = ScraperRunLogService(ScraperRunLogRepository(db_session))
    run = history.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
    )
    logs.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.ERROR,
        step="failed",
        message="Detail page okunamadı: https://foodist.test/brand/x",
    )
    history.fail_run(run.id, error_message="Detail page okunamadı: https://foodist.test/brand/x")
    db_session.flush()

    response = client.get(f"/api/v1/scraper/runs/{run.id}/logs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_status"] == "failed"
    assert any(item["level"] == "error" and item["step"] == "failed" for item in payload["items"])
