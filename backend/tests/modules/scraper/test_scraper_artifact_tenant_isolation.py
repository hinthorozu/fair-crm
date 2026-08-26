"""P0.1 TI-07 adversarial coverage for scraper artifact ownership."""

from datetime import UTC, datetime

from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import (
    is_safe_handoff_artifact_path,
    resolve_handoff_excel_path,
)
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _sample_handoff() -> ScraperImportHandoff:
    return ScraperImportHandoff(
        canonical_rows=[{"company_name": "Artifact Owner", "website": "", "email": "", "phone": ""}],
    )


def test_handoff_artifact_path_requires_matching_run_under_handoff_root(tmp_path):
    service_run_id = __import__("uuid").uuid4()
    other_run_id = __import__("uuid").uuid4()

    own_path = resolve_handoff_excel_path(service_run_id, base_dir=tmp_path)
    foreign_path = resolve_handoff_excel_path(other_run_id, base_dir=tmp_path)
    outside_path = tmp_path.parent / f"{service_run_id}.xlsx"

    assert is_safe_handoff_artifact_path(own_path, run_id=service_run_id, base_dir=tmp_path)
    assert not is_safe_handoff_artifact_path(foreign_path, run_id=service_run_id, base_dir=tmp_path)
    assert not is_safe_handoff_artifact_path(outside_path, run_id=service_run_id, base_dir=tmp_path)


def test_excel_download_ignores_corrupt_stored_path_to_another_run(
    client,
    db_session,
    auth_headers,
    organization_id,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.modules.scraper.infrastructure.handoff_storage.DEFAULT_HANDOFF_DIR",
        tmp_path,
    )

    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    owner_run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://owner-artifact.test",
        fair_name="Owner Artifact Fair",
        fair_year=2026,
        organization_id=organization_id,
        handoff=_sample_handoff(),
    )
    foreign_artifact_run = service.record_completed_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        started_at=datetime.now(UTC),
        input_url="https://foreign-artifact.test",
        fair_name="Foreign Artifact Fair",
        fair_year=2026,
        organization_id=organization_id,
        handoff=_sample_handoff(),
    )

    foreign_path = resolve_handoff_excel_path(foreign_artifact_run.id, base_dir=tmp_path)
    foreign_path.parent.mkdir(parents=True, exist_ok=True)
    foreign_path.write_bytes(b"foreign artifact bytes")

    owner_model = db_session.get(ScraperRunHistoryModel, owner_run.id)
    assert owner_model is not None
    owner_model.output_excel_path = str(foreign_path.resolve())
    db_session.commit()

    scoped = service.get_run_for_organization(owner_run.id, organization_id)
    assert scoped is not None
    assert scoped.output_excel_path is None

    response = client.get(
        f"/api/v1/scraper/runs/{owner_run.id}/output/excel",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.content != b"foreign artifact bytes"
