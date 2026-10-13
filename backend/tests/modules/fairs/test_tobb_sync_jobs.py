from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from app.modules.fairs.application.tobb_sync_job_runner import TobbSyncJobRunner
from app.modules.fairs.application.tobb_weekly_sync import weekly_years
from app.modules.fairs.application.sync_tobb_system_fairs import SyncTobbSystemFairsUseCase
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.tobb_calendar import TobbFairRow
from app.modules.fairs.infrastructure.tobb_run_repository import SqlAlchemyTobbRunRepository


class Reader:
    def __init__(self):
        self.fail_year = 2027
        self.years = []
        self.extra_row = False

    def read(self, year):
        self.years.append(year)
        if year == self.fail_year:
            raise ValueError("provider unavailable")
        rows = [TobbFairRow("1", "EXAMPLE FAIR", None, None, "İstanbul", date(year, 11, 1), date(year, 11, 4), None)]
        if self.extra_row:
            rows.append(TobbFairRow("2", "ANOTHER FAIR", None, None, "Ankara", date(year, 11, 1), date(year, 11, 4), None))
        return rows


def _worker(db_session, monkeypatch):
    reader = Reader()
    factory = sessionmaker(bind=db_session.get_bind())
    worker = TobbSyncJobRunner(factory, reader)
    monkeypatch.setattr(worker, "_notify", lambda repository, run: None)
    return worker, reader, factory


def test_automatic_years_have_independent_partial_success_and_retry(db_session, monkeypatch, client, auth_headers):
    from app.integrations.kyrox_core.super_admin import get_super_admin_reader
    from app.modules.fairs.api.tobb_review_routes import get_tobb_job_runner
    worker, reader, _ = _worker(db_session, monkeypatch)
    run, _ = SqlAlchemyTobbRunRepository(db_session).start([2026, 2027], requested_by=None, automatic=True)
    worker.run(run.id)
    db_session.expire_all()
    saved = SqlAlchemyTobbRunRepository(db_session).get(run.id)
    assert saved.status == "failed"
    assert saved.organization_id is None
    assert saved.summary_json["year_results"]["2026"]["status"] == "completed"
    assert saved.summary_json["year_results"]["2027"]["attempts"] == 3
    fair = db_session.query(FairModel).one()
    original_id = fair.id
    assert reader.years == [2026, 2027, 2027, 2027]
    reader.fail_year = None
    client.app.dependency_overrides[get_super_admin_reader] = lambda: lambda token, org: True
    client.app.dependency_overrides[get_tobb_job_runner] = lambda: worker
    response = client.post(f"/api/v1/fairs/system/tobb/runs/{run.id}/retry", headers=auth_headers)
    assert response.status_code == 202, response.text
    db_session.expire_all()
    saved = SqlAlchemyTobbRunRepository(db_session).get(run.id)
    assert saved.status == "completed"
    assert reader.years == [2026, 2027, 2027, 2027, 2027]
    assert db_session.query(FairModel).one().id == original_id
    assert len(saved.summary_json["retry_history"]) == 1


def test_cooperative_cancel_preserves_only_committed_fairs(db_session, monkeypatch):
    worker, reader, factory = _worker(db_session, monkeypatch)
    reader.extra_row = True
    run, _ = SqlAlchemyTobbRunRepository(db_session).start([2026], requested_by=None, automatic=True)
    execute = SyncTobbSystemFairsUseCase.execute

    def execute_and_cancel(self, year, **kwargs):
        commit_item = kwargs["committed_item"]
        def committed(detail):
            commit_item(detail)
            with factory() as cancellation:
                current = SqlAlchemyTobbRunRepository(cancellation).get(run.id)
                current.status = "cancel_requested"
                current.cancel_requested_at = datetime.now(UTC)
                cancellation.commit()
        return execute(self, year, **{**kwargs, "committed_item": committed})

    monkeypatch.setattr(SyncTobbSystemFairsUseCase, "execute", execute_and_cancel)
    worker.run(run.id)
    db_session.expire_all()
    saved = SqlAlchemyTobbRunRepository(db_session).get(run.id)
    assert saved.status == "cancelled" and saved.error_message is None
    assert db_session.query(FairModel).count() == 1
    assert db_session.query(FairModel).one().name == "EXAMPLE FAIR"
    assert saved.summary_json["year_results"]["2026"]["details"][0]["name"] == "EXAMPLE FAIR"


def test_queued_cancellation_terminalizes_before_any_fetch(db_session, monkeypatch):
    worker, reader, _ = _worker(db_session, monkeypatch)
    run, _ = SqlAlchemyTobbRunRepository(db_session).start([2026], requested_by=None, automatic=True)
    run.status = "cancel_requested"
    db_session.commit()
    worker.run(run.id)
    db_session.expire_all()
    assert SqlAlchemyTobbRunRepository(db_session).get(run.id).status == "cancelled"
    assert reader.years == []
    assert db_session.query(FairModel).count() == 0


def test_weekly_timer_and_years_follow_istanbul_without_catchup():
    assert weekly_years(datetime(2026, 12, 31, 22, 0, tzinfo=UTC)) == [2027, 2028]
    root = Path(__file__).resolve().parents[4]
    timer = (root / "scripts/server/systemd/fair-crm-tobb-sync.timer").read_text()
    assert "OnCalendar=Mon *-*-* 03:00:00 Europe/Istanbul" in timer
    assert "Persistent=false" in timer
