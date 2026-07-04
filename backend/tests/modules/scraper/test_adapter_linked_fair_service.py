"""Tests for adapter linked fair service."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.adapter_linked_fair_service import AdapterLinkedFairService
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _seed_fair(db_session, organization_id, *, name: str) -> FairModel:
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
        created_at=now,
        updated_at=now,
        deleted_at=None,
        archived_from_status=None,
    )
    db_session.add(fair)
    db_session.flush()
    return fair


def test_list_linked_fairs_from_run_history(db_session, organization_id):
    fair = _seed_fair(db_session, organization_id, name="Foodist Expo")
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    history.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        started_at=datetime.now(UTC),
    )
    db_session.flush()

    service = AdapterLinkedFairService(db_session)
    fairs = service.list_linked_fairs(organization_id, ScraperSiteKey.TUYAP_NEW)

    assert len(fairs) == 1
    assert fairs[0].id == fair.id
    assert fairs[0].name == "Foodist Expo"
    assert fairs[0].venue == "TÜYAP"
    assert fairs[0].city == "İstanbul"
    assert fairs[0].status == FairStatus.ACTIVE.value
    assert fairs[0].source_url == "https://foodist.test/list"


def test_list_linked_fairs_includes_unmatched_run_fair_name(db_session, organization_id):
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    history.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        input_url="https://unknown.test/list",
        fair_name="Unknown Fair",
        fair_year=2026,
        started_at=datetime.now(UTC),
    )
    db_session.flush()

    service = AdapterLinkedFairService(db_session)
    fairs = service.list_linked_fairs(organization_id, ScraperSiteKey.TUYAP_NEW)

    assert len(fairs) == 1
    assert fairs[0].id is None
    assert fairs[0].name == "Unknown Fair"
    assert fairs[0].source_url == "https://unknown.test/list"


def test_list_linked_fairs_uses_latest_import_batch_time(db_session, organization_id):
    fair = _seed_fair(db_session, organization_id, name="Foodist Expo")
    history = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    run = history.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime(2026, 6, 1, tzinfo=UTC),
        input_url="https://foodist.test/list",
        fair_name="Foodist Expo",
        fair_year=2026,
        handoff=ScraperImportHandoff(canonical_rows=[{"company_name": "Demo"}]),
        finished_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )
    _ = run
    db_session.add(
        ImportBatchModel(
            id=uuid4(),
            organization_id=organization_id,
            fair_id=fair.id,
            source_type="excel",
            file_name="foodist.xlsx",
            status="completed",
            total_rows=1,
            valid_rows=1,
            invalid_rows=0,
            duplicate_rows=0,
            created_rows=1,
            updated_rows=0,
            skipped_rows=0,
            created_participations=0,
            updated_participations=0,
            column_mapping_json=None,
            raw_preview_json=None,
            has_header_row=True,
            header_mode="first_row",
            header_row_index=None,
            selected_sheet_name=None,
            stored_file_content=None,
            created_at=datetime(2026, 6, 30, 10, 20, tzinfo=UTC),
            updated_at=datetime(2026, 6, 30, 10, 20, tzinfo=UTC),
            notes=None,
        )
    )
    db_session.flush()

    service = AdapterLinkedFairService(db_session)
    fairs = service.list_linked_fairs(organization_id, ScraperSiteKey.TUYAP_NEW)

    assert len(fairs) == 1
    assert fairs[0].last_import_at == datetime(2026, 6, 30, 10, 20, tzinfo=UTC)


def test_unknown_adapter_raises(db_session, organization_id):
    service = AdapterLinkedFairService(db_session)
    try:
        service.list_linked_fairs(organization_id, "unknown")
        assert False, "expected KeyError"
    except KeyError:
        pass
