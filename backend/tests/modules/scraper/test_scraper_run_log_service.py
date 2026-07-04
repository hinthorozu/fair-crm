"""Tests for scraper run console log service."""

from datetime import UTC, datetime, timedelta

from app.modules.scraper.domain.scraper_run_log import ScraperRunLogLevel
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.infrastructure.repositories.scraper_run_log_repository import ScraperRunLogRepository
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import ScraperRunLogService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _start_run(db_session):
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    return history.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
    )


def test_append_log_persists_record(db_session):
    run = _start_run(db_session)
    service = ScraperRunLogService(ScraperRunLogRepository(db_session))

    log = service.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.INFO,
        step="started",
        message="TÜYAP New adapter çalışıyor",
        metadata={"adapter_key": ScraperSiteKey.TUYAP_NEW},
    )
    db_session.flush()

    assert log.run_id == run.id
    assert log.level == ScraperRunLogLevel.INFO
    assert log.step == "started"
    assert log.metadata == {"adapter_key": ScraperSiteKey.TUYAP_NEW}


def test_list_logs_returns_chronological_order(db_session):
    run = _start_run(db_session)
    service = ScraperRunLogService(ScraperRunLogRepository(db_session))
    base = datetime.now(UTC)

    first = service.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.INFO,
        step="started",
        message="started",
        created_at=base,
    )
    second = service.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.INFO,
        step="list_scrape_started",
        message="list",
        created_at=base + timedelta(seconds=1),
    )
    third = service.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.SUCCESS,
        step="completed",
        message="done",
        created_at=base + timedelta(seconds=2),
    )
    db_session.flush()

    logs = service.list_logs(run.id)

    assert [item.id for item in logs] == [first.id, second.id, third.id]
    assert [item.level for item in logs] == [
        ScraperRunLogLevel.INFO,
        ScraperRunLogLevel.INFO,
        ScraperRunLogLevel.SUCCESS,
    ]


def test_list_logs_supports_after_id_polling(db_session):
    run = _start_run(db_session)
    service = ScraperRunLogService(ScraperRunLogRepository(db_session))
    base = datetime.now(UTC)

    first = service.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.INFO,
        step="started",
        message="started",
        created_at=base,
    )
    service.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.ERROR,
        step="failed",
        message="boom",
        created_at=base + timedelta(seconds=1),
    )
    db_session.flush()

    incremental = service.list_logs(run.id, after_id=first.id)

    assert len(incremental) == 1
    assert incremental[0].level == ScraperRunLogLevel.ERROR
    assert incremental[0].step == "failed"


def test_failed_run_can_have_error_log(db_session):
    run = _start_run(db_session)
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    log_service = ScraperRunLogService(ScraperRunLogRepository(db_session))

    log_service.append_log(
        run_id=run.id,
        level=ScraperRunLogLevel.ERROR,
        step="failed",
        message="Network timeout",
    )
    history.fail_run(run.id, error_message="Network timeout")
    db_session.flush()

    logs = log_service.list_logs(run.id)
    failed_run = history.get_run(run.id)

    assert failed_run is not None
    assert failed_run.status.value == "failed"
    assert any(item.level == ScraperRunLogLevel.ERROR and item.step == "failed" for item in logs)
