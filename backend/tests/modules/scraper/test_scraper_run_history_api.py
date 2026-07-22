"""Tests for scraper run history API."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import (
    resolve_handoff_excel_path,
    resolve_handoff_path,
)
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


def test_list_scraper_runs_returns_recorded_runs(client: TestClient, db_session, auth_headers, organization_id):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        organization_id=organization_id,
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


def test_get_scraper_run_by_id(client: TestClient, db_session, auth_headers, organization_id):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        organization_id=organization_id,
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


def test_dashboard_summary_uses_run_history(client: TestClient, db_session, auth_headers, organization_id):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_OLD,
        started_at=datetime.now(UTC),
        input_url="https://old.test",
        fair_name="Old",
        fair_year=2024,
        organization_id=organization_id,
        error_message="old failure",
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://new.test",
        fair_name="Foodist",
        fair_year=2026,
        organization_id=organization_id,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    response = client.get("/api/v1/scraper/dashboard", headers=auth_headers)

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["last_run_adapter"] == ScraperSiteKey.TUYAP_NEW
    assert summary["failed_scraper_count"] == 1


def test_list_scraper_runs_filters_by_adapter_key(client: TestClient, db_session, auth_headers, organization_id):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://new.test",
        fair_name="Foodist",
        fair_year=2026,
        organization_id=organization_id,
        handoff=_sample_handoff(),
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_OLD,
        started_at=datetime.now(UTC),
        input_url="https://old.test",
        fair_name="Old",
        fair_year=2024,
        organization_id=organization_id,
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


def test_list_scraper_runs_filters_by_status(client: TestClient, db_session, auth_headers, organization_id):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://failed.test",
        fair_name="Foodist",
        fair_year=2026,
        organization_id=organization_id,
        error_message="timeout",
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://ok.test",
        fair_name="Foodist",
        fair_year=2026,
        organization_id=organization_id,
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


def test_delete_scraper_run_removes_history_row(
    client: TestClient, db_session, auth_headers, organization_id
):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://delete-me.test",
        fair_name="Delete Me Fair",
        fair_year=2026,
        organization_id=organization_id,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    response = client.delete(f"/api/v1/scraper/runs/{run.id}", headers=auth_headers)

    assert response.status_code == 204
    list_response = client.get("/api/v1/scraper/runs", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0
    assert all(item["id"] != str(run.id) for item in list_response.json()["items"])
    assert service.get_run(run.id) is None


def test_delete_scraper_run_not_found(client: TestClient, auth_headers):
    response = client.delete(
        "/api/v1/scraper/runs/00000000-0000-0000-0000-000000000001",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_scraper_run_rejects_active_run(
    client: TestClient, db_session, auth_headers, organization_id
):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        input_url="https://active.test",
        fair_name="Active Fair",
        fair_year=2026,
        organization_id=organization_id,
    )
    db_session.flush()

    response = client.delete(f"/api/v1/scraper/runs/{run.id}", headers=auth_headers)

    assert response.status_code == 409
    assert "Aktif" in response.json()["detail"]
    assert service.get_run(run.id) is not None


def test_delete_scraper_run_preserves_fair_and_import_batch(
    client: TestClient, db_session, auth_headers, organization_id
):
    from app.modules.imports.infrastructure.persistence.models import ImportBatchModel

    fair_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Preserve Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://preserve.test/list",
        },
        headers=auth_headers,
    )
    assert fair_response.status_code == 201
    fair_id = fair_response.json()["id"]

    now = datetime.now(UTC)
    import_batch_id = uuid4()
    db_session.add(
        ImportBatchModel(
            id=import_batch_id,
            organization_id=organization_id,
            fair_id=UUID(fair_id),
            source_type="scraper",
            file_name="preserve-test.json",
            status="completed",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=now,
        input_url="https://preserve.test/list",
        fair_name="Preserve Fair",
        fair_year=2026,
        organization_id=organization_id,
        fair_id=UUID(fair_id),
        handoff=_sample_handoff(),
        import_batch_id=import_batch_id,
    )
    db_session.flush()

    response = client.delete(f"/api/v1/scraper/runs/{run.id}", headers=auth_headers)
    assert response.status_code == 204

    fair_get = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert fair_get.status_code == 200
    assert fair_get.json()["name"] == "Preserve Fair"

    batch_get = client.get(f"/api/v1/imports/{import_batch_id}", headers=auth_headers)
    assert batch_get.status_code == 200
    assert batch_get.json()["id"] == str(import_batch_id)
    assert db_session.get(ImportBatchModel, import_batch_id) is not None


def test_delete_scraper_run_removes_only_own_handoff_artifacts(
    client: TestClient, db_session, auth_headers, organization_id, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "app.modules.scraper.infrastructure.handoff_storage.DEFAULT_HANDOFF_DIR",
        tmp_path,
    )

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://artifact.test",
        fair_name="Artifact Fair",
        fair_year=2026,
        organization_id=organization_id,
        handoff=_sample_handoff(),
    )
    other_run_id = uuid4()
    own_json = resolve_handoff_path(run.id, base_dir=tmp_path)
    own_excel = resolve_handoff_excel_path(run.id, base_dir=tmp_path)
    other_json = resolve_handoff_path(other_run_id, base_dir=tmp_path)
    own_json.parent.mkdir(parents=True, exist_ok=True)
    own_json.write_text('{"ok": true}\n', encoding="utf-8")
    own_excel.write_bytes(b"xlsx")
    other_json.write_text('{"keep": true}\n', encoding="utf-8")
    db_session.flush()

    response = client.delete(f"/api/v1/scraper/runs/{run.id}", headers=auth_headers)

    assert response.status_code == 204
    assert not own_json.exists()
    assert not own_excel.exists()
    assert other_json.exists()
