from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.integrations.kyrox_core.auth import create_test_token
from app.integrations.kyrox_core.super_admin import get_super_admin_reader
from app.modules.fairs.api.tobb_review_routes import get_tobb_job_runner
from app.modules.fairs.application.tobb_sync_job_runner import TobbSyncJobRunner
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.tobb_calendar import TobbFairRow
from app.modules.fairs.infrastructure.tobb_run_repository import SqlAlchemyTobbRunRepository


class Reader:
    def __init__(self):
        self.years = []
        self.fail = False
        self.rows = [TobbFairRow("7", "Win Eurasia", "TUYAP", "Tuyap", "İstanbul",
                                 date(2026, 9, 1), date(2026, 9, 5), "https://example.test")]

    def read(self, year):
        self.years.append(year)
        if self.fail:
            raise ValueError("TOBB calendar request timed out")
        return self.rows


@pytest.fixture
def runner(client, db_session, monkeypatch):
    reader = Reader()
    worker = TobbSyncJobRunner(sessionmaker(bind=db_session.get_bind()), reader)
    monkeypatch.setattr(worker, "_notify", lambda repository, run: None)
    client.app.dependency_overrides[get_tobb_job_runner] = lambda: worker
    return worker


def _super_admin(client):
    client.app.dependency_overrides[get_super_admin_reader] = lambda: lambda token, org: True


def _preview(client, headers):
    response = client.post("/api/v1/fairs/system/tobb/sync", headers=headers, json={"year": 2026})
    assert response.status_code == 202, response.text
    run_id = response.json()["run"]["id"]
    return run_id, client.get(f"/api/v1/fairs/system/tobb/runs/{run_id}", headers=headers).json()


def test_super_admin_preview_does_not_write_fairs_until_explicit_apply(client, db_session, auth_headers, runner):
    _super_admin(client)
    run_id, run = _preview(client, auth_headers)
    assert runner.reader.years == [2026]
    assert run["summary"]["phase"] == "preview_ready"
    assert run["summary"]["year_results"]["2026"]["inserted"] == 1
    assert db_session.query(FairModel).count() == 0
    applied = client.post(f"/api/v1/fairs/system/tobb/runs/{run_id}/apply", headers=auth_headers)
    assert applied.status_code == 202, applied.text
    saved = db_session.query(FairModel).one()
    assert (saved.origin, saved.organization_id, saved.source, saved.external_id) == ("system", None, "tobb", "2026:7")
    final = client.get(f"/api/v1/fairs/system/tobb/runs/{run_id}", headers=auth_headers).json()
    assert final["status"] == "completed"
    assert final["summary"]["year_results"]["2026"]["inserted"] == 1


def test_organization_admin_cannot_sync_or_read_reviews(client, auth_headers, runner):
    assert client.post("/api/v1/fairs/system/tobb/sync", headers=auth_headers, json={"year": 2026}).status_code == 403
    assert client.get("/api/v1/fairs/system/tobb/reviews", headers=auth_headers).status_code == 403
    assert runner.reader.years == []


def test_organization_user_cannot_sync_or_read_history(client, organization_id, runner):
    headers = {"Authorization": f"Bearer {create_test_token(user_id=uuid4())}", "X-Organization-Id": str(organization_id)}
    assert client.post("/api/v1/fairs/system/tobb/sync", headers=headers, json={"year": 2026}).status_code == 403
    assert client.get("/api/v1/fairs/system/tobb/runs", headers=headers).status_code == 403
    assert runner.reader.years == []


def test_failed_fetch_is_recorded_after_three_bounded_attempts(client, db_session, auth_headers, runner):
    _super_admin(client)
    runner.reader.fail = True
    _, run = _preview(client, auth_headers)
    assert run["status"] == "failed"
    assert run["summary"]["year_results"]["2026"]["attempts"] == 3
    assert run["summary"]["year_results"]["2026"]["error"] == "TOBB calendar request timed out"
    assert db_session.query(FairModel).count() == 0


def test_unseen_changed_source_blocks_preview_application(client, db_session, auth_headers, runner):
    _super_admin(client)
    run_id, _ = _preview(client, auth_headers)
    runner.reader.rows = [TobbFairRow("8", "Unseen fair", None, None, "Ankara", date(2026, 11, 1), date(2026, 11, 4), None)]
    assert client.post(f"/api/v1/fairs/system/tobb/runs/{run_id}/apply", headers=auth_headers).status_code == 202
    run = client.get(f"/api/v1/fairs/system/tobb/runs/{run_id}", headers=auth_headers).json()
    assert run["summary"]["year_results"]["2026"]["status"] == "preview_stale"
    assert db_session.query(FairModel).count() == 0


def test_second_request_returns_existing_global_active_job(client, db_session, auth_headers, runner):
    _super_admin(client)
    active, created = SqlAlchemyTobbRunRepository(db_session).start([2026, 2027], requested_by=None, automatic=True)
    assert created
    response = client.post("/api/v1/fairs/system/tobb/sync", headers=auth_headers, json={"year": 2026})
    assert response.status_code == 202
    assert response.json()["started"] is False
    assert response.json()["run"]["id"] == str(active.id)
    assert runner.reader.years == []


def test_stale_review_response_preserves_current_state_as_json(client, auth_headers, runner, monkeypatch):
    from app.modules.fairs.application.tobb_workflow_service import TobbWorkflowService
    from app.modules.fairs.domain.exceptions import TobbReviewConflict

    _super_admin(client)
    current = {"id": str(uuid4()), "version": 2, "status": "approved"}

    def conflict(self, payload, *, auth, access_token):
        raise TobbReviewConflict("Karar daha önce kaydedildi", current)

    monkeypatch.setattr(TobbWorkflowService, "decide", conflict)
    response = client.post("/api/v1/fairs/system/tobb/reviews/decide", headers=auth_headers,
                           json={"id": current["id"], "version": 1, "decision": "keep"})
    assert response.status_code == 409
    assert response.json()["detail"]["current"] == current


def test_run_history_can_reach_older_pages(client, db_session, auth_headers, runner):
    _super_admin(client)
    repository = SqlAlchemyTobbRunRepository(db_session)
    ids = set()
    for _ in range(51):
        run, created = repository.start([2026], requested_by=None, automatic=True)
        assert created
        ids.add(str(run.id))
        run.status = "completed"
        db_session.commit()
    first = client.get("/api/v1/fairs/system/tobb/runs", headers=auth_headers)
    second = client.get("/api/v1/fairs/system/tobb/runs?offset=50", headers=auth_headers)
    assert first.status_code == second.status_code == 200
    assert len(first.json()["items"]) == 50 and len(second.json()["items"]) == 1
    assert {row["id"] for row in first.json()["items"] + second.json()["items"]} == ids
    assert client.get("/api/v1/fairs/system/tobb/runs?offset=-1", headers=auth_headers).status_code == 422


def test_bulk_dates_commits_valid_item_and_retains_invalid_pending_item(client, db_session, auth_headers, runner):
    from datetime import UTC, datetime
    from app.modules.fairs.infrastructure.tobb_review_repository import SqlAlchemyTobbReviewRepository

    _super_admin(client)
    repository = SqlAlchemyTobbReviewRepository(db_session)
    fairs = []
    for index in range(2):
        now = datetime.now(UTC)
        fair = FairModel(id=uuid4(), origin="system", organization_id=None, source="tobb", name=f"Bulk {index}", normalized_name=f"BULK {index}",
                         status="planned", start_date=date(2026, 10, 20), end_date=date(2026, 10, 23),
                         created_at=now, updated_at=now)
        db_session.add(fair)
        db_session.flush()
        fairs.append(fair)
        repository.propose(kind="dates", fair_id=fair.id, name=fair.name,
                           stored={"start_date": "2026-10-20", "end_date": "2026-10-23", "_date_revision": 0},
                           proposed={"start_date": "2026-11-11", "end_date": "2026-11-14" if index == 0 else None}, source={})
    rows = repository.list_pending()
    response = client.post("/api/v1/fairs/system/tobb/reviews/dates/bulk", headers=auth_headers,
                           json={"items": [{"id": row["id"], "version": row["version"], "decision": "apply"} for row in rows]})
    assert response.status_code == 200
    assert [item["success"] for item in response.json()["items"]] == [True, False]
    db_session.expire_all()
    assert (fairs[0].start_date, fairs[0].end_date) == (date(2026, 11, 11), date(2026, 11, 14))
    assert (fairs[1].start_date, fairs[1].end_date) == (date(2026, 10, 20), date(2026, 10, 23))
    assert [row["fair_id"] for row in repository.list_pending()] == [str(fairs[1].id)]
