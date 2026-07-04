"""Tests for adapter delete preview and delete API."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _create_adapter(client: TestClient, auth_headers: dict[str, str], adapter_key: str, name: str) -> None:
    response = client.post(
        "/api/v1/scraper/adapters",
        json={
            "adapter_key": adapter_key,
            "name": name,
            "engine_key": ScraperSiteKey.TUYAP_NEW,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201


def _create_linked_fair(
    db_session: Session,
    organization_id,
    *,
    name: str,
    adapter_key: str,
) -> FairModel:
    now = datetime.now(UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name=name,
        organizer=None,
        venue="TÜYAP",
        city="İstanbul",
        country="Türkiye",
        start_date=None,
        end_date=None,
        website=None,
        status=FairStatus.ACTIVE.value,
        description=None,
        normalized_name=compute_normalized_name(name=name),
        adapter_key=adapter_key,
        source_url="https://example.test/list",
        created_at=now,
        updated_at=now,
        deleted_at=None,
        archived_from_status=None,
    )
    db_session.add(fair)
    db_session.flush()
    return fair


def test_delete_preview_for_adapter_without_links(client: TestClient, auth_headers):
    _create_adapter(client, auth_headers, "preview_clean", "Preview Clean")

    response = client.get(
        "/api/v1/scraper/adapters/preview_clean/delete-preview",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["adapter_key"] == "preview_clean"
    assert body["display_name"] == "Preview Clean"
    assert body["linked_fairs_count"] == 0
    assert body["active_runs_count"] == 0
    assert body["affected_fairs"] == []
    assert body["active_runs"] == []


def test_delete_custom_adapter_removes_from_list(client: TestClient, auth_headers):
    _create_adapter(client, auth_headers, "to_delete", "To Delete")

    delete = client.delete("/api/v1/scraper/adapters/to_delete", headers=auth_headers)
    assert delete.status_code == 204

    get = client.get("/api/v1/scraper/adapters/to_delete", headers=auth_headers)
    assert get.status_code == 404

    listing = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    keys = {item["adapter_key"] for item in listing.json()["items"]}
    assert "to_delete" not in keys


def test_delete_adapter_unlinks_fairs(
    client: TestClient,
    auth_headers,
    db_session: Session,
    organization_id,
):
    adapter_key = "linked_fair_adapter"
    _create_adapter(client, auth_headers, adapter_key, "Linked Fair Adapter")
    fair = _create_linked_fair(
        db_session,
        organization_id,
        name="Linked Fair",
        adapter_key=adapter_key,
    )

    preview = client.get(
        f"/api/v1/scraper/adapters/{adapter_key}/delete-preview",
        headers=auth_headers,
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["linked_fairs_count"] == 1
    assert preview_body["affected_fairs"] == ["Linked Fair"]

    delete = client.delete(f"/api/v1/scraper/adapters/{adapter_key}", headers=auth_headers)
    assert delete.status_code == 204

    db_session.expire(fair)
    assert fair.adapter_key is None


def test_delete_adapter_removes_running_run(
    client: TestClient,
    auth_headers,
    db_session: Session,
    organization_id,
):
    adapter_key = "running_jobs_adapter"
    _create_adapter(client, auth_headers, adapter_key, "Running Jobs Adapter")
    now = datetime.now(UTC)
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = history.start_run(
        adapter_key=adapter_key,
        input_url="https://example.test/list",
        fair_name="Test Fair",
        fair_year=2026,
        organization_id=organization_id,
        started_at=now,
    )
    db_session.flush()

    preview = client.get(
        f"/api/v1/scraper/adapters/{adapter_key}/delete-preview",
        headers=auth_headers,
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["active_runs_count"] == 1
    assert len(preview_body["active_runs"]) == 1
    assert preview_body["active_runs"][0]["id"] == str(run.id)

    delete = client.delete(f"/api/v1/scraper/adapters/{adapter_key}", headers=auth_headers)
    assert delete.status_code == 204

    assert history.get_run(run.id) is None


def test_delete_adapter_removes_all_run_history(
    client: TestClient,
    auth_headers,
    db_session: Session,
    organization_id,
):
    adapter_key = "history_cleanup_adapter"
    _create_adapter(client, auth_headers, adapter_key, "History Cleanup Adapter")
    now = datetime.now(UTC)
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))

    running = history.start_run(
        adapter_key=adapter_key,
        input_url="https://example.test/running",
        fair_name="Running Fair",
        fair_year=2026,
        organization_id=organization_id,
        started_at=now,
    )
    completed = history.start_run(
        adapter_key=adapter_key,
        input_url="https://example.test/completed",
        fair_name="Completed Fair",
        fair_year=2026,
        organization_id=organization_id,
        started_at=now,
    )
    history.complete_run(
        completed.id,
        handoff=ScraperImportHandoff(canonical_rows=[{"company_name": "Acme"}], row_metadata=[]),
        finished_at=now,
    )
    failed = history.start_run(
        adapter_key=adapter_key,
        input_url="https://example.test/failed",
        fair_name="Failed Fair",
        fair_year=2026,
        organization_id=organization_id,
        started_at=now,
    )
    history.fail_run(failed.id, error_message="boom", finished_at=now)
    db_session.flush()

    other = history.start_run(
        adapter_key="other_adapter",
        input_url="https://example.test/other",
        fair_name="Other Fair",
        fair_year=2026,
        organization_id=organization_id,
        started_at=now,
    )
    db_session.flush()

    delete = client.delete(f"/api/v1/scraper/adapters/{adapter_key}", headers=auth_headers)
    assert delete.status_code == 204

    assert history.get_run(running.id) is None
    assert history.get_run(completed.id) is None
    assert history.get_run(failed.id) is None
    assert history.get_run(other.id) is not None

    runs = client.get("/api/v1/scraper/runs", headers=auth_headers)
    assert runs.status_code == 200
    adapter_keys = {item["adapter_key"] for item in runs.json()["items"]}
    assert adapter_key not in adapter_keys
    assert "other_adapter" in adapter_keys


def test_delete_registry_adapter_hidden_from_list(client: TestClient, auth_headers):
    preview = client.get(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/delete-preview",
        headers=auth_headers,
    )
    assert preview.status_code == 200
    assert preview.json()["adapter_key"] == ScraperSiteKey.TUYAP_NEW

    delete = client.delete(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}",
        headers=auth_headers,
    )
    assert delete.status_code == 204

    get = client.get(
        f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}",
        headers=auth_headers,
    )
    assert get.status_code == 404

    listing = client.get("/api/v1/scraper/adapters", headers=auth_headers)
    keys = {item["adapter_key"] for item in listing.json()["items"]}
    assert ScraperSiteKey.TUYAP_NEW not in keys
