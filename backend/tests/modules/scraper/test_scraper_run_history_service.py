"""Tests for scraper run history service."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_history_service import (
    ScraperRunHistoryService,
    compute_handoff_metrics,
)
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _sample_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[
            {
                "company_name": "Alpha Co",
                "website": "https://alpha.test",
                "email": "a@alpha.test",
                "phone": "111",
            },
            {
                "company_name": "Beta Co",
                "website": "",
                "email": "",
                "phone": "222",
            },
            {
                "company_name": "Gamma Co",
                "website": "https://gamma.test",
                "email": "g@gamma.test",
                "phone": "",
            },
        ],
        row_metadata=[
            {"instagram_url": "https://instagram.com/alpha"},
            {},
            {
                "linkedin_url": "https://linkedin.com/company/gamma",
                "facebook_url": "https://facebook.com/gamma",
                "youtube_url": "https://youtube.com/@gamma",
                "x_url": "https://x.com/gamma",
            },
        ],
    )


def test_compute_handoff_metrics_counts_fields():
    metrics = compute_handoff_metrics(_sample_handoff())

    assert metrics == {
        "total_rows": 3,
        "website_count": 2,
        "email_count": 2,
        "phone_count": 2,
        "instagram_count": 1,
        "linkedin_count": 1,
        "facebook_count": 1,
        "youtube_count": 1,
        "x_count": 1,
    }


def test_record_completed_run_persists_metrics(db_session):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    started_at = datetime.now(UTC)

    run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=started_at,
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        handoff=_sample_handoff(),
        output_json_path="/tmp/handoff.json",
        output_excel_path="/tmp/handoff.xlsx",
    )
    db_session.flush()

    assert run.status == ScraperRunStatus.COMPLETED
    assert run.adapter_key == ScraperSiteKey.TUYAP_NEW
    assert run.total_rows == 3
    assert run.website_count == 2
    assert run.email_count == 2
    assert run.phone_count == 2
    assert run.instagram_count == 1
    assert run.linkedin_count == 1
    assert run.error_message is None
    assert run.duration_ms is not None
    assert run.duration_ms >= 0


def test_record_failed_run_persists_error(db_session):
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    started_at = datetime.now(UTC) - timedelta(seconds=5)

    run = service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=started_at,
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        error_message="Network timeout",
    )
    db_session.flush()

    assert run.status == ScraperRunStatus.FAILED
    assert run.error_message == "Network timeout"
    assert run.total_rows == 0
    assert run.website_count == 0
    assert run.duration_ms is not None
    assert run.duration_ms >= 5000


def test_dashboard_run_stats_use_latest_and_failed_count(db_session):
    org_id = uuid4()
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    base = datetime.now(UTC)

    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_OLD,
        started_at=base - timedelta(minutes=10),
        input_url="https://old.test",
        fair_name="Old Fair",
        fair_year=2024,
        organization_id=org_id,
        handoff=_sample_handoff(),
    )
    service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=base - timedelta(minutes=5),
        input_url="https://new.test",
        fair_name="Foodist",
        fair_year=2025,
        organization_id=org_id,
        error_message="boom",
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=base,
        input_url="https://new.test",
        fair_name="Foodist",
        fair_year=2026,
        organization_id=org_id,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    stats = service.get_dashboard_run_stats(org_id)

    assert stats["last_run_adapter"] == ScraperSiteKey.TUYAP_NEW
    assert stats["failed_scraper_count"] == 1


def test_dashboard_run_stats_are_organization_scoped(db_session):
    org_a = uuid4()
    org_b = uuid4()
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    base = datetime.now(UTC)
    service.record_failed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=base - timedelta(minutes=5),
        input_url="https://new.test",
        fair_name="Foodist",
        fair_year=2025,
        organization_id=org_a,
        error_message="boom",
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=base,
        input_url="https://new.test",
        fair_name="Foodist",
        fair_year=2026,
        organization_id=org_a,
        handoff=_sample_handoff(),
    )
    service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_OLD,
        started_at=base,
        input_url="https://old.test",
        fair_name="Old",
        fair_year=2026,
        organization_id=org_b,
        handoff=_sample_handoff(),
    )
    db_session.flush()

    stats_a = service.get_dashboard_run_stats(org_a)
    stats_b = service.get_dashboard_run_stats(org_b)

    assert stats_a["last_run_adapter"] == ScraperSiteKey.TUYAP_NEW
    assert stats_a["failed_scraper_count"] == 1
    assert stats_b["last_run_adapter"] == ScraperSiteKey.TUYAP_OLD
    assert stats_b["failed_scraper_count"] == 0
