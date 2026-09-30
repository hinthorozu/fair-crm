from datetime import UTC, datetime
from uuid import UUID, uuid4

import app.modules.fairs.api.dependencies as fairs_dependencies
import app.modules.scraper.application.fair_scraper_job_runner as job_runner_module
from app.integrations.kyrox_core.auth import create_test_token
from app.integrations.kyrox_core.super_admin import get_super_admin_reader
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.scraper.application.fair_scraper_job_runner import FairScraperJobCommand, FairScraperJobRunner
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _sample_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[{"company_name": "Demo Co", "website": "", "email": "", "phone": ""}],
        row_metadata=[{}],
    )


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
    )


def _run_job(db_session, organization_id, user_id, fair_id, executor):
    runner = FairScraperJobRunner(session_factory=lambda: db_session, scrape_executor=executor)
    previous = fairs_dependencies._fair_scraper_job_runner
    fairs_dependencies._fair_scraper_job_runner = runner
    return runner, previous


def test_organization_fair_scrape_still_creates_import_batch(
    client, auth_headers, db_session, organization_id, user_id, monkeypatch
):
    calls = {"import": 0, "scrape": 0}
    original = job_runner_module.create_and_analyze_import_batch_from_handoff

    def _import_spy(*args, **kwargs):
        calls["import"] += 1
        return original(*args, **kwargs)

    def _scrape(**_kwargs):
        calls["scrape"] += 1
        return _sample_handoff()

    monkeypatch.setattr(job_runner_module, "create_and_analyze_import_batch_from_handoff", _import_spy)
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Org Scraper Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = create_response.json()["id"]

    runner, previous = _run_job(db_session, organization_id, user_id, fair_id, _scrape)
    try:
        response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
    finally:
        fairs_dependencies._fair_scraper_job_runner = previous

    assert response.status_code == 202
    assert response.json()["organization_id"] == str(organization_id)
    runner.run_fair_scraper(
        FairScraperJobCommand(
            run_id=UUID(response.json()["id"]),
            organization_id=organization_id,
            fair_id=UUID(fair_id),
            user_id=user_id,
        )
    )
    db_session.expire_all()
    completed = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session)).get_run(
        UUID(response.json()["id"])
    )
    assert calls["scrape"] >= 1
    assert calls["import"] >= 1
    assert completed is not None
    assert completed.import_batch_id is not None
    assert completed.total_rows == 1


def test_system_fair_scrape_completes_without_import_batch(
    client, auth_headers, db_session, organization_id, user_id, monkeypatch
):
    calls = {"import": 0, "scrape": 0}

    def _import_spy(*_args, **_kwargs):
        calls["import"] += 1
        raise AssertionError("system fair scrape must not create an import batch")

    def _scrape(**_kwargs):
        calls["scrape"] += 1
        return _sample_handoff()

    monkeypatch.setattr(job_runner_module, "create_and_analyze_import_batch_from_handoff", _import_spy)
    system = SqlAlchemyFairRepository(db_session).add(_system_fair("System Scraper Fair"))

    runner, previous = _run_job(db_session, organization_id, user_id, system.id, _scrape)
    client.app.dependency_overrides[get_super_admin_reader] = lambda: (
        lambda _access_token, _organization_id: True
    )
    try:
        response = client.post(f"/api/v1/fairs/{system.id}/run", headers=auth_headers)
    finally:
        fairs_dependencies._fair_scraper_job_runner = previous

    assert response.status_code == 202
    body = response.json()
    assert body["organization_id"] is None
    assert body["fair_id"] == str(system.id)
    assert body["status"] == "running"

    runner.run_fair_scraper(
        FairScraperJobCommand(
            run_id=UUID(body["id"]),
            organization_id=organization_id,
            fair_id=system.id,
            user_id=user_id,
        )
    )
    db_session.expire_all()
    completed = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session)).get_run(UUID(body["id"]))
    assert calls["scrape"] >= 1
    assert calls["import"] == 0
    assert completed is not None
    assert completed.status.value == "completed"
    assert completed.finished_at is not None
    assert completed.output_json_path is not None
    assert completed.total_rows == 1
    assert completed.organization_id is None
    assert completed.import_batch_id is None
    batches = (
        db_session.query(ImportBatchModel)
        .filter(ImportBatchModel.fair_id == system.id)
        .count()
    )
    assert batches == 0


def test_other_organization_fair_scraper_stays_not_found(
    client, auth_headers, other_organization_id, user_id
):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": "Private Scraper Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
        },
        headers=auth_headers,
    )
    fair_id = create_response.json()["id"]
    other_headers = {
        "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
        "X-Organization-Id": str(other_organization_id),
    }
    response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=other_headers)
    assert response.status_code == 404
