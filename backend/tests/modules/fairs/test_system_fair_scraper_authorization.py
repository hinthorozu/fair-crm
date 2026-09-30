from datetime import UTC, datetime
from uuid import uuid4

import httpx

from app.integrations.kyrox_core.auth import create_test_token
from app.integrations.kyrox_core.client import KyroxCoreHttpClient
from app.integrations.kyrox_core.super_admin import get_super_admin_reader
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.scraper.infrastructure.handoff_storage import (
    resolve_handoff_excel_path,
    resolve_handoff_path,
)
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _system_fair(name: str) -> Fair:
    now = datetime.now(tz=UTC)
    return Fair(
        id=uuid4(),
        organization_id=None,
        name=name,
        organizer=None,
        venue=None,
        city=None,
        country="Türkiye",
        start_date=None,
        end_date=None,
        website=None,
        status=FairStatus.PLANNED,
        description=None,
        normalized_name=compute_normalized_name(name=name),
        created_at=now,
        updated_at=now,
        deleted_at=None,
        origin="system",
        source="tobb",
        external_id=f"2026:{uuid4().hex[:8]}",
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        source_url="https://foodist.test/brands",
        scraper_config={"page_limit": 1},
    )


def _headers(user_id, organization_id):
    return {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(organization_id),
    }


def _as_super_admin(client) -> None:
    client.app.dependency_overrides[get_super_admin_reader] = lambda: (
        lambda _access_token, _organization_id: True
    )


def _add_run(db_session, *, fair_id, organization_id, status: str):
    now = datetime.now(tz=UTC)
    run = ScraperRunHistoryModel(
        id=uuid4(),
        adapter_key="tuyap_new",
        status=status,
        started_at=now,
        finished_at=None if status == "running" else now,
        organization_id=organization_id,
        fair_id=fair_id,
        total_rows=1,
        website_count=0,
        email_count=0,
        phone_count=0,
        instagram_count=0,
        linkedin_count=0,
        facebook_count=0,
        youtube_count=0,
        x_count=0,
        run_source="fair_automation",
    )
    db_session.add(run)
    db_session.flush()
    return run


def _runs_for_fair(db_session, fair_id):
    return (
        db_session.query(ScraperRunHistoryModel)
        .filter(ScraperRunHistoryModel.fair_id == fair_id)
        .all()
    )


def test_context_lookup_failure_is_not_super_admin():
    client = KyroxCoreHttpClient(base_url="http://core.test")

    def _down(*_args, **_kwargs):
        raise httpx.ConnectError("down")

    client.request = _down
    assert client.read_is_super_admin(access_token="token", organization_id=uuid4()) is False

    class _Response:
        status_code = 200
        text = "{}"

        def json(self):
            return {"is_super_admin": "yes"}

    client.request = lambda *_args, **_kwargs: _Response()
    assert client.read_is_super_admin(access_token="token", organization_id=uuid4()) is False


def test_organization_admin_cannot_start_system_fair_scraper(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Blocked Start Fair"))
    run = client.post(f"/api/v1/fairs/{fair.id}/run", headers=auth_headers)
    alias = client.post(f"/api/v1/fairs/{fair.id}/scraper-runs", headers=auth_headers)
    assert run.status_code == 403
    assert alias.status_code == 403
    assert _runs_for_fair(db_session, fair.id) == []


def test_super_admin_can_start_system_fair_scraper(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Admin Start Fair"))
    _as_super_admin(client)
    response = client.post(f"/api/v1/fairs/{fair.id}/run", headers=auth_headers)
    assert response.status_code == 202
    assert response.json()["organization_id"] is None
    stored = _runs_for_fair(db_session, fair.id)
    assert len(stored) == 1
    assert stored[0].organization_id is None


def test_organization_admin_cannot_update_system_fair(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Blocked Update Fair"))
    response = client.patch(
        f"/api/v1/fairs/{fair.id}",
        headers=auth_headers,
        json={"description": "changed", "scraper_config": {"page_limit": 9}},
    )
    assert response.status_code == 403
    db_session.expire_all()
    stored = db_session.get(FairModel, fair.id)
    assert stored.description is None
    assert stored.scraper_config == {"page_limit": 1}


def test_super_admin_can_update_system_fair(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Admin Update Fair"))
    _as_super_admin(client)
    response = client.patch(
        f"/api/v1/fairs/{fair.id}",
        headers=auth_headers,
        json={
            "description": "Admin note",
            "source_url": "https://foodist.test/updated",
            "scraper_config": {"page_limit": 4},
        },
    )
    assert response.status_code == 200, response.text
    db_session.expire_all()
    stored = db_session.get(FairModel, fair.id)
    assert stored.organization_id is None
    assert stored.description == "Admin note"
    assert stored.scraper_config == {"page_limit": 4}
    assert stored.source_url


def test_organization_admin_cannot_manage_null_system_runs(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Hidden Run Fair"))
    completed = _add_run(db_session, fair_id=fair.id, organization_id=None, status="completed")
    running = _add_run(db_session, fair_id=fair.id, organization_id=None, status="running")
    listed = client.get(f"/api/v1/scraper/runs?fair_id={fair.id}", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["items"] == []
    assert client.get(f"/api/v1/scraper/runs/{completed.id}", headers=auth_headers).status_code == 404
    assert client.get(f"/api/v1/scraper/runs/{completed.id}/logs", headers=auth_headers).status_code == 404
    assert client.get(f"/api/v1/scraper/runs/{completed.id}/output/json", headers=auth_headers).status_code == 404
    assert client.get(f"/api/v1/scraper/runs/{completed.id}/output/excel", headers=auth_headers).status_code == 404
    assert client.post(f"/api/v1/scraper/runs/{running.id}/cancel", headers=auth_headers).status_code == 404
    assert client.delete(f"/api/v1/scraper/runs/{completed.id}", headers=auth_headers).status_code == 404
    assert db_session.get(ScraperRunHistoryModel, completed.id) is not None


def test_super_admin_can_manage_null_system_runs(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Visible Run Fair"))
    completed = _add_run(db_session, fair_id=fair.id, organization_id=None, status="completed")
    running = _add_run(db_session, fair_id=fair.id, organization_id=None, status="running")
    json_path = resolve_handoff_path(completed.id)
    excel_path = resolve_handoff_excel_path(completed.id)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text('{"rows":[]}\n', encoding="utf-8")
    excel_path.write_bytes(b"excel")
    _as_super_admin(client)
    try:
        listed = client.get(f"/api/v1/scraper/runs?fair_id={fair.id}", headers=auth_headers)
        assert listed.status_code == 200
        assert {item["id"] for item in listed.json()["items"]} >= {str(completed.id), str(running.id)}
        assert client.get(f"/api/v1/scraper/runs/{completed.id}", headers=auth_headers).status_code == 200
        assert client.get(f"/api/v1/scraper/runs/{completed.id}/logs", headers=auth_headers).status_code == 200
        assert client.get(f"/api/v1/scraper/runs/{completed.id}/output/json", headers=auth_headers).status_code == 200
        assert client.get(f"/api/v1/scraper/runs/{completed.id}/output/excel", headers=auth_headers).status_code == 200
        cancelled = client.post(f"/api/v1/scraper/runs/{running.id}/cancel", headers=auth_headers)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancel_requested"
        deleted = client.delete(f"/api/v1/scraper/runs/{completed.id}", headers=auth_headers)
        assert deleted.status_code == 204
        db_session.expire_all()
        assert db_session.get(ScraperRunHistoryModel, completed.id) is None
    finally:
        json_path.unlink(missing_ok=True)
        excel_path.unlink(missing_ok=True)


def test_organization_run_history_stays_tenant_scoped(
    client, db_session, organization_id, other_organization_id, user_id
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Tenant History Fair"))
    run_a = _add_run(db_session, fair_id=fair.id, organization_id=organization_id, status="completed")
    run_b = _add_run(db_session, fair_id=fair.id, organization_id=other_organization_id, status="completed")
    system_run = _add_run(db_session, fair_id=fair.id, organization_id=None, status="completed")
    headers_a = _headers(user_id, organization_id)
    headers_b = _headers(user_id, other_organization_id)
    listed_a = client.get(f"/api/v1/scraper/runs?fair_id={fair.id}", headers=headers_a)
    listed_b = client.get(f"/api/v1/scraper/runs?fair_id={fair.id}", headers=headers_b)
    ids_a = {item["id"] for item in listed_a.json()["items"]}
    ids_b = {item["id"] for item in listed_b.json()["items"]}
    assert ids_a == {str(run_a.id)}
    assert ids_b == {str(run_b.id)}
    assert str(system_run.id) not in ids_a
    assert str(system_run.id) not in ids_b
    assert client.get(f"/api/v1/scraper/runs/{run_b.id}", headers=headers_a).status_code == 404
    assert client.get(f"/api/v1/scraper/runs/{run_a.id}", headers=headers_b).status_code == 404
