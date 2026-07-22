"""Scraper API tenant and permission security tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.integrations.kyrox_core.auth import create_test_token
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.scraper.api.dependencies import (
    PERMISSION_CREATE,
    PERMISSION_DELETE,
    PERMISSION_DOWNLOAD,
    PERMISSION_READ,
    PERMISSION_RUN,
    PERMISSION_UPDATE,
    get_authorization_adapter as get_scraper_authorization_adapter,
)
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


class SelectiveAuthorization(AuthorizationPort):
    def __init__(self, *, denied: set[str] | None = None) -> None:
        self._denied = denied or set()

    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (organization_id, user_id, access_token)
        return permission_code not in self._denied


def _sample_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[{"company_name": "Demo", "website": "", "email": "", "phone": ""}],
    )


def _seed_completed_run(db_session, organization_id: UUID):
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
    return run


def test_unauthenticated_scraper_runs_returns_401(client: TestClient, organization_id):
    response = client.get(
        "/api/v1/scraper/runs",
        headers={"X-Organization-Id": str(organization_id)},
    )
    assert response.status_code == 401


def test_unauthenticated_scraper_dashboard_returns_401(client: TestClient, organization_id):
    response = client.get(
        "/api/v1/scraper/dashboard",
        headers={"X-Organization-Id": str(organization_id)},
    )
    assert response.status_code == 401


def test_unauthenticated_run_logs_returns_401(client: TestClient, organization_id):
    response = client.get(
        "/api/v1/scraper/runs/00000000-0000-0000-0000-000000000001/logs",
        headers={"X-Organization-Id": str(organization_id)},
    )
    assert response.status_code == 401


def test_scraper_read_permission_denied_returns_403(client: TestClient, auth_headers):
    client.app.dependency_overrides[get_scraper_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_READ}
    )
    try:
        response = client.get("/api/v1/scraper/runs", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_scraper_authorization_adapter, None)


def test_scraper_create_permission_denied_returns_403(client: TestClient, auth_headers):
    client.app.dependency_overrides[get_scraper_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_CREATE}
    )
    try:
        response = client.post(
            "/api/v1/scraper/adapters",
            json={"name": "Denied Adapter", "engine_key": ScraperSiteKey.TUYAP_NEW},
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_scraper_authorization_adapter, None)


def test_scraper_update_permission_denied_returns_403(client: TestClient, auth_headers):
    create = client.post(
        "/api/v1/scraper/adapters",
        json={"name": "Patch Target", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )
    assert create.status_code == 201
    adapter_key = create.json()["adapter_key"]

    client.app.dependency_overrides[get_scraper_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_UPDATE}
    )
    try:
        response = client.patch(
            f"/api/v1/scraper/adapters/{adapter_key}",
            json={"name": "Renamed"},
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_scraper_authorization_adapter, None)


def test_scraper_delete_permission_denied_returns_403(client: TestClient, auth_headers):
    create = client.post(
        "/api/v1/scraper/adapters",
        json={"name": "Delete Target", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )
    assert create.status_code == 201
    adapter_key = create.json()["adapter_key"]

    client.app.dependency_overrides[get_scraper_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_DELETE}
    )
    try:
        response = client.delete(f"/api/v1/scraper/adapters/{adapter_key}", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_scraper_authorization_adapter, None)


def test_scraper_run_delete_permission_denied_returns_403(
    client: TestClient,
    auth_headers,
    db_session,
    organization_id,
):
    run = _seed_completed_run(db_session, organization_id)
    client.app.dependency_overrides[get_scraper_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_DELETE}
    )
    try:
        response = client.delete(f"/api/v1/scraper/runs/{run.id}", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_scraper_authorization_adapter, None)


def test_scraper_run_delete_not_visible_from_other_organization(
    client: TestClient,
    auth_headers,
    other_organization_id,
    user_id,
    db_session,
    organization_id,
):
    run = _seed_completed_run(db_session, organization_id)
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }

    response = client.delete(f"/api/v1/scraper/runs/{run.id}", headers=other_headers)
    assert response.status_code == 404
    assert ScraperRunHistoryService(ScraperRunHistoryRepository(db_session)).get_run(run.id) is not None


def test_scraper_run_permission_denied_returns_403(client: TestClient, auth_headers):
    client.app.dependency_overrides[get_scraper_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_RUN}
    )
    try:
        response = client.post(
            f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/test-run",
            json={"input_url": "https://foodist.test/list"},
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_scraper_authorization_adapter, None)


def test_scraper_download_permission_denied_returns_403(
    client: TestClient,
    auth_headers,
    db_session,
    organization_id,
    tmp_path,
    monkeypatch,
):
    run = _seed_completed_run(db_session, organization_id)
    json_path = tmp_path / f"{run.id}.json"
    json_path.write_text('{"rows": []}', encoding="utf-8")
    monkeypatch.setattr(
        "app.modules.scraper.api.routes.resolve_handoff_path",
        lambda run_id: tmp_path / f"{run_id}.json",
    )

    client.app.dependency_overrides[get_scraper_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_DOWNLOAD}
    )
    try:
        response = client.get(
            f"/api/v1/scraper/runs/{run.id}/output/json",
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_scraper_authorization_adapter, None)


def test_run_detail_not_visible_from_other_organization(
    client: TestClient,
    auth_headers,
    other_organization_id,
    user_id,
    db_session,
    organization_id,
):
    run = _seed_completed_run(db_session, organization_id)
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }

    response = client.get(f"/api/v1/scraper/runs/{run.id}", headers=other_headers)
    assert response.status_code == 404


def test_run_logs_not_visible_from_other_organization(
    client: TestClient,
    auth_headers,
    other_organization_id,
    user_id,
    db_session,
    organization_id,
):
    run = _seed_completed_run(db_session, organization_id)
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }

    response = client.get(f"/api/v1/scraper/runs/{run.id}/logs", headers=other_headers)
    assert response.status_code == 404


def test_json_download_not_available_from_other_organization(
    client: TestClient,
    auth_headers,
    other_organization_id,
    user_id,
    db_session,
    organization_id,
    tmp_path,
    monkeypatch,
):
    run = _seed_completed_run(db_session, organization_id)
    json_path = tmp_path / f"{run.id}.json"
    json_path.write_text('{"rows": []}', encoding="utf-8")
    monkeypatch.setattr(
        "app.modules.scraper.api.routes.resolve_handoff_path",
        lambda run_id: tmp_path / f"{run_id}.json",
    )

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.get(f"/api/v1/scraper/runs/{run.id}/output/json", headers=other_headers)
    assert response.status_code == 404


def test_null_organization_run_not_visible_in_tenant_api(
    client: TestClient,
    auth_headers,
    db_session,
):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://legacy.test/list",
        fair_name="Legacy",
        fair_year=2024,
        organization_id=None,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    response = client.get(f"/api/v1/scraper/runs/{run.id}", headers=auth_headers)
    assert response.status_code == 404


def test_get_run_row_by_id_requires_exact_organization_match(db_session):
    org_a = uuid4()
    org_b = uuid4()
    repository = ScraperRunHistoryRepository(db_session)
    service = ScraperRunHistoryService(repository)
    run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        organization_id=org_a,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    assert repository.get_run_row_by_id(run.id, organization_id=org_a) is not None
    assert repository.get_run_row_by_id(run.id, organization_id=org_b) is None


def test_adapter_list_is_organization_scoped(
    client: TestClient,
    auth_headers,
    other_organization_id,
    user_id,
):
    create = client.post(
        "/api/v1/scraper/adapters",
        json={"name": "Org A Adapter", "engine_key": ScraperSiteKey.TUYAP_NEW},
        headers=auth_headers,
    )
    assert create.status_code == 201
    adapter_key = create.json()["adapter_key"]

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    listing = client.get("/api/v1/scraper/adapters", headers=other_headers)
    assert listing.status_code == 200
    keys = {item["adapter_key"] for item in listing.json()["items"]}
    assert adapter_key not in keys


def test_dashboard_run_stats_are_organization_scoped(
    client: TestClient,
    auth_headers,
    other_organization_id,
    user_id,
    db_session,
    organization_id,
):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://org-a.test",
        fair_name="Org A Fair",
        fair_year=2026,
        organization_id=organization_id,
        error_message="failed",
    )
    db_session.flush()

    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.get("/api/v1/scraper/dashboard", headers=other_headers)
    assert response.status_code == 200
    assert response.json()["summary"]["failed_scraper_count"] == 0

    own_response = client.get("/api/v1/scraper/dashboard", headers=auth_headers)
    assert own_response.status_code == 200
    assert own_response.json()["summary"]["failed_scraper_count"] == 1
