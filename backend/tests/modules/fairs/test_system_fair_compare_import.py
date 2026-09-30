from datetime import UTC, datetime
from uuid import uuid4

from app.integrations.kyrox_core.auth import create_test_token
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.imports.application.analyze_canonical_import import AnalyzeCanonicalImportUseCase
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import (
    resolve_handoff_path,
    write_handoff_json,
)
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel


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
    )


def _add_run(db_session, *, fair_id, status: str, total_rows: int, finished_at, organization_id=None, started_at=None):
    started = started_at or finished_at or datetime.now(tz=UTC)
    run = ScraperRunHistoryModel(
        id=uuid4(),
        adapter_key="tuyap_new",
        status=status,
        started_at=started,
        finished_at=finished_at,
        organization_id=organization_id,
        fair_id=fair_id,
        total_rows=total_rows,
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


def _sample_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[{"company_name": "Demo Co", "website": "", "email": "", "phone": ""}],
        row_metadata=[{}],
    )


def _write_handoff(run, fair_id) -> str:
    return write_handoff_json(
        _sample_handoff(),
        run.id,
        adapter_key="tuyap_new",
        fair_id=fair_id,
        source_url="https://foodist.test/brands",
    )


def _headers(user_id, organization_id) -> dict[str, str]:
    token = create_test_token(user_id=user_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(organization_id),
    }


def _batches(db_session, fair_id):
    return db_session.query(ImportBatchModel).filter(ImportBatchModel.fair_id == fair_id).all()


def _compare(client, headers, fair_id):
    return client.post(f"/api/v1/fairs/{fair_id}/compare-import", headers=headers)


def test_compare_import_creates_batch_and_runs_analyze(
    client, auth_headers, db_session, organization_id, monkeypatch
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Compare Fair"))
    run = _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=1,
        finished_at=datetime(2026, 3, 15, tzinfo=UTC),
    )
    path = _write_handoff(run, fair.id)
    run.output_json_path = path
    db_session.flush()

    calls = {"analyze": 0}
    original = AnalyzeCanonicalImportUseCase.execute

    def _spy(self, *args, **kwargs):
        calls["analyze"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(AnalyzeCanonicalImportUseCase, "execute", _spy)
    try:
        response = _compare(client, auth_headers, fair.id)
        assert response.status_code == 201
        batch_id = response.json()["batch_id"]
        batches = _batches(db_session, fair.id)
        assert len(batches) == 1
        batch = batches[0]
        assert str(batch.id) == batch_id
        assert batch.organization_id == organization_id
        assert batch.fair_id == fair.id
        assert batch.organization_id is not None
        assert fair.organization_id is None
        assert batch.status == "decision_required"
        assert calls["analyze"] == 1
    finally:
        resolve_handoff_path(run.id).unlink(missing_ok=True)


def test_two_organizations_get_separate_batches(
    client, db_session, organization_id, other_organization_id, user_id
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Shared System Fair"))
    run = _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=1,
        finished_at=datetime(2026, 3, 15, tzinfo=UTC),
    )
    _write_handoff(run, fair.id)
    run.output_json_path = str(resolve_handoff_path(run.id))
    db_session.flush()
    headers_a = _headers(user_id, organization_id)
    headers_b = _headers(user_id, other_organization_id)
    try:
        first = _compare(client, headers_a, fair.id)
        second = _compare(client, headers_b, fair.id)
        assert first.status_code == 201
        assert second.status_code == 201
        batch_a = first.json()["batch_id"]
        batch_b = second.json()["batch_id"]
        assert batch_a != batch_b
        stored = {str(row.id): row for row in _batches(db_session, fair.id)}
        assert stored[batch_a].organization_id == organization_id
        assert stored[batch_b].organization_id == other_organization_id
        assert client.get(f"/api/v1/data-integration/imports/{batch_b}", headers=headers_a).status_code == 404
        assert client.get(f"/api/v1/data-integration/imports/{batch_a}", headers=headers_b).status_code == 404
    finally:
        resolve_handoff_path(run.id).unlink(missing_ok=True)


def test_missing_completed_run_does_not_create_batch(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("No Run Fair"))
    response = _compare(client, auth_headers, fair.id)
    assert response.status_code == 400
    assert _batches(db_session, fair.id) == []


def test_newer_failed_or_running_run_does_not_replace_completed_handoff(
    client, auth_headers, db_session
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Older Completed Fair"))
    completed = _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=1,
        finished_at=datetime(2026, 1, 1, tzinfo=UTC),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    _write_handoff(completed, fair.id)
    completed.output_json_path = str(resolve_handoff_path(completed.id))
    _add_run(
        db_session,
        fair_id=fair.id,
        status="failed",
        total_rows=999,
        finished_at=datetime(2026, 6, 1, tzinfo=UTC),
        started_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    _add_run(
        db_session,
        fair_id=fair.id,
        status="running",
        total_rows=50,
        finished_at=None,
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    db_session.flush()
    try:
        response = _compare(client, auth_headers, fair.id)
        assert response.status_code == 201
        batches = _batches(db_session, fair.id)
        assert len(batches) == 1
        assert batches[0].total_rows == 1
    finally:
        resolve_handoff_path(completed.id).unlink(missing_ok=True)


def test_missing_output_path_does_not_create_batch(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("No Path Fair"))
    _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=1,
        finished_at=datetime(2026, 3, 15, tzinfo=UTC),
    )
    response = _compare(client, auth_headers, fair.id)
    assert response.status_code == 400
    assert _batches(db_session, fair.id) == []


def test_unreadable_handoff_does_not_create_batch(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Bad File Fair"))
    run = _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=1,
        finished_at=datetime(2026, 3, 15, tzinfo=UTC),
    )
    path = resolve_handoff_path(run.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json", encoding="utf-8")
    run.output_json_path = str(path)
    db_session.flush()
    try:
        response = _compare(client, auth_headers, fair.id)
        assert response.status_code == 400
        assert _batches(db_session, fair.id) == []
    finally:
        path.unlink(missing_ok=True)


def test_missing_handoff_file_does_not_create_batch(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Missing File Fair"))
    run = _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=1,
        finished_at=datetime(2026, 3, 15, tzinfo=UTC),
    )
    run.output_json_path = str(resolve_handoff_path(run.id))
    db_session.flush()
    response = _compare(client, auth_headers, fair.id)
    assert response.status_code == 400
    assert _batches(db_session, fair.id) == []


def test_other_organization_fair_is_not_found(
    client, auth_headers, db_session, other_organization_id
):
    now = datetime.now(tz=UTC)
    fair = SqlAlchemyFairRepository(db_session).add(
        Fair.create(organization_id=other_organization_id, name="Other Org Fair", now=now)
    )
    response = _compare(client, auth_headers, fair.id)
    assert response.status_code == 404
    assert _batches(db_session, fair.id) == []


def test_organization_fair_compare_is_rejected(client, auth_headers, db_session, organization_id):
    now = datetime.now(tz=UTC)
    fair = SqlAlchemyFairRepository(db_session).add(
        Fair.create(organization_id=organization_id, name="Own Org Fair", now=now)
    )
    response = _compare(client, auth_headers, fair.id)
    assert response.status_code == 403
    assert _batches(db_session, fair.id) == []
