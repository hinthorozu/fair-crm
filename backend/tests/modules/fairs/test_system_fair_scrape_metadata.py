from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import event

from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
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


def _add_run(
    db_session,
    *,
    fair_id,
    status: str,
    total_rows: int,
    finished_at: datetime | None,
    organization_id=None,
    started_at: datetime | None = None,
) -> None:
    started = started_at or finished_at or datetime.now(tz=UTC)
    db_session.add(
        ScraperRunHistoryModel(
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
    )
    db_session.flush()


def _detail(client, auth_headers, fair_id):
    response = client.get(f"/api/v1/fairs/{fair_id}", headers=auth_headers)
    assert response.status_code == 200
    return response.json()


def test_unscraped_system_fair_metadata_is_null(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Unscraped Fair"))
    body = _detail(client, auth_headers, fair.id)
    assert body["origin"] == "system"
    assert body["organization_id"] is None
    assert body["scraped_record_count"] is None
    assert body["scraped_at"] is None


def test_completed_run_metadata_is_returned(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Scraped Fair"))
    finished = datetime(2026, 3, 15, 10, 30, tzinfo=UTC)
    _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=427,
        finished_at=finished,
    )
    body = _detail(client, auth_headers, fair.id)
    assert body["scraped_record_count"] == 427
    assert body["scraped_at"].startswith("2026-03-15T10:30:00")


def test_latest_completed_run_wins(client, auth_headers, db_session):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Several Runs Fair"))
    _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=10,
        finished_at=datetime(2026, 1, 1, tzinfo=UTC),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=427,
        finished_at=datetime(2026, 6, 1, tzinfo=UTC),
        started_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    body = _detail(client, auth_headers, fair.id)
    assert body["scraped_record_count"] == 427
    assert body["scraped_at"].startswith("2026-06-01")


def test_newer_unsuccessful_run_does_not_replace_completed_metadata(
    client, auth_headers, db_session
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Failed After Success Fair"))
    _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=427,
        finished_at=datetime(2026, 6, 1, tzinfo=UTC),
        started_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    later = datetime(2026, 8, 1, tzinfo=UTC)
    for status in ("failed", "running", "cancelled"):
        _add_run(
            db_session,
            fair_id=fair.id,
            status=status,
            total_rows=999,
            finished_at=None if status == "running" else later,
            started_at=later + timedelta(minutes=1),
        )
    body = _detail(client, auth_headers, fair.id)
    assert body["scraped_record_count"] == 427
    assert body["scraped_at"].startswith("2026-06-01")


def test_other_fair_and_organization_runs_do_not_mix(
    client, auth_headers, db_session, organization_id
):
    fair = SqlAlchemyFairRepository(db_session).add(_system_fair("Target Fair"))
    other = SqlAlchemyFairRepository(db_session).add(_system_fair("Other Fair"))
    _add_run(
        db_session,
        fair_id=other.id,
        status="completed",
        total_rows=88,
        finished_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=12,
        finished_at=datetime(2026, 2, 1, tzinfo=UTC),
        organization_id=organization_id,
    )
    _add_run(
        db_session,
        fair_id=fair.id,
        status="completed",
        total_rows=427,
        finished_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    body = _detail(client, auth_headers, fair.id)
    assert body["scraped_record_count"] == 427
    assert body["scraped_at"].startswith("2026-03-01")


def test_list_reads_system_fair_metadata_in_one_history_query(
    client, auth_headers, db_session
):
    repo = SqlAlchemyFairRepository(db_session)
    fairs = [repo.add(_system_fair(f"Listed Fair {index}")) for index in range(3)]
    _add_run(
        db_session,
        fair_id=fairs[0].id,
        status="completed",
        total_rows=427,
        finished_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    statements: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany):
        if "scraper_run_history" in statement.lower():
            statements.append(statement)

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", _capture)
    try:
        response = client.get("/api/v1/fairs", headers=auth_headers)
    finally:
        event.remove(bind, "before_cursor_execute", _capture)

    assert response.status_code == 200
    assert len(statements) == 1
    items = {item["id"]: item for item in response.json()["items"]}
    assert items[str(fairs[0].id)]["scraped_record_count"] == 427
    assert items[str(fairs[1].id)]["scraped_record_count"] is None
    assert items[str(fairs[2].id)]["scraped_at"] is None
