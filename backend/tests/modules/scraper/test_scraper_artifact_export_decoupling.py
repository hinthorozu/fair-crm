"""Tests: scrape success must not fail when secondary artifact exports fail."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import app.modules.fairs.api.dependencies as fairs_dependencies
from app.modules.scraper.application.fair_scraper_job_runner import FairScraperJobCommand, FairScraperJobRunner
from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.modules.scraper.exporters.scraper_artifact_export import (
    ArtifactExportBundle,
    ArtifactExportResult,
    export_scraper_artifacts,
)
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.adapter_instance_resolver import AdapterOutputFormats
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _sample_handoff(*, rows: int = 1) -> ScraperImportHandoff:
    canonical_rows = [
        {"company_name": f"Demo Co {index}", "website": "", "email": "", "phone": ""}
        for index in range(rows)
    ]
    return ScraperImportHandoff(
        canonical_rows=canonical_rows,
        row_metadata=[{} for _ in canonical_rows],
    )


def _mock_scrape_executor(**_kwargs) -> ScraperImportHandoff:
    return _sample_handoff()


def _start_fair_run(client, auth_headers, organization_id, user_id, db_session, *, excel: bool = True):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": f"Artifact Decouple Fair {uuid4().hex[:8]}",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
            "scraper_config": {"use_http": True},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = create_response.json()["id"]

    if excel:
        client.patch(
            f"/api/v1/scraper/adapters/{ScraperSiteKey.TUYAP_NEW}/manifest",
            json={"output": {"json_handoff": True, "excel": True}},
            headers=auth_headers,
        )

    mock_runner = FairScraperJobRunner(session_factory=lambda: db_session, scrape_executor=_mock_scrape_executor)
    previous_runner = fairs_dependencies._fair_scraper_job_runner
    fairs_dependencies._fair_scraper_job_runner = mock_runner
    try:
        response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
    finally:
        fairs_dependencies._fair_scraper_job_runner = previous_runner

    assert response.status_code == 202
    run_id = UUID(response.json()["id"])
    return mock_runner, run_id, UUID(fair_id), organization_id, user_id


def test_export_scraper_artifacts_all_succeed(tmp_path):
    handoff = _sample_handoff()
    run_id = uuid4()
    bundle = export_scraper_artifacts(
        handoff,
        run_id,
        output_formats=AdapterOutputFormats(json_handoff=True, excel=True),
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        source_url="https://example.test/list",
        base_dir=tmp_path,
    )
    assert bundle.json_path is not None
    assert bundle.excel_path is not None
    assert bundle.has_failures is False
    assert bundle.warning_message() is None


def test_export_scraper_artifacts_excel_failure_keeps_json(tmp_path):
    handoff = _sample_handoff()
    run_id = uuid4()

    with patch(
        "app.modules.scraper.exporters.scraper_artifact_export.write_handoff_excel_file",
        side_effect=RuntimeError("excel boom"),
    ):
        bundle = export_scraper_artifacts(
            handoff,
            run_id,
            output_formats=AdapterOutputFormats(json_handoff=True, excel=True),
            adapter_key=ScraperSiteKey.TUYAP_NEW,
            source_url="https://example.test/list",
            base_dir=tmp_path,
        )

    assert bundle.json_path is not None
    assert bundle.excel_path is None
    assert bundle.has_failures is True
    assert "excel" in (bundle.warning_message() or "")
    assert "excel boom" in (bundle.warning_message() or "")


def test_export_scraper_artifacts_json_failure_keeps_excel_when_requested(tmp_path):
    handoff = _sample_handoff()
    run_id = uuid4()

    with patch(
        "app.modules.scraper.exporters.scraper_artifact_export.write_handoff_json",
        side_effect=RuntimeError("json boom"),
    ):
        bundle = export_scraper_artifacts(
            handoff,
            run_id,
            output_formats=AdapterOutputFormats(json_handoff=True, excel=True),
            adapter_key=ScraperSiteKey.TUYAP_NEW,
            source_url="https://example.test/list",
            base_dir=tmp_path,
        )

    assert bundle.json_path is None
    assert bundle.excel_path is not None
    assert "json boom" in (bundle.warning_message() or "")


def test_fair_runner_scrape_success_json_and_excel_success(
    client, auth_headers, db_session, organization_id, user_id
):
    mock_runner, run_id, fair_id, org_id, uid = _start_fair_run(
        client, auth_headers, organization_id, user_id, db_session, excel=True
    )
    mock_runner.run_fair_scraper(
        FairScraperJobCommand(run_id=run_id, organization_id=org_id, fair_id=fair_id, user_id=uid)
    )
    db_session.expire_all()
    completed = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session)).get_run(run_id)
    assert completed is not None
    assert completed.status == ScraperRunStatus.COMPLETED
    assert completed.total_rows == 1
    assert completed.output_json_path is not None
    assert completed.output_excel_path is not None
    assert completed.error_message is None


def test_fair_runner_excel_failure_keeps_completed_and_json(
    client, auth_headers, db_session, organization_id, user_id
):
    mock_runner, run_id, fair_id, org_id, uid = _start_fair_run(
        client, auth_headers, organization_id, user_id, db_session, excel=True
    )
    with patch(
        "app.modules.scraper.exporters.scraper_artifact_export.write_handoff_excel_file",
        side_effect=OSError("disk full"),
    ):
        mock_runner.run_fair_scraper(
            FairScraperJobCommand(run_id=run_id, organization_id=org_id, fair_id=fair_id, user_id=uid)
        )
    db_session.expire_all()
    completed = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session)).get_run(run_id)
    assert completed is not None
    assert completed.status == ScraperRunStatus.COMPLETED
    assert completed.total_rows == 1
    assert completed.output_json_path is not None
    assert completed.output_excel_path is None
    assert completed.error_message is not None
    assert "excel" in completed.error_message.lower() or "disk full" in completed.error_message


def test_fair_runner_json_failure_does_not_mark_scrape_failed(
    client, auth_headers, db_session, organization_id, user_id
):
    mock_runner, run_id, fair_id, org_id, uid = _start_fair_run(
        client, auth_headers, organization_id, user_id, db_session, excel=True
    )
    with patch(
        "app.modules.scraper.exporters.scraper_artifact_export.write_handoff_json",
        side_effect=ValueError("canonical invalid"),
    ):
        mock_runner.run_fair_scraper(
            FairScraperJobCommand(run_id=run_id, organization_id=org_id, fair_id=fair_id, user_id=uid)
        )
    db_session.expire_all()
    completed = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session)).get_run(run_id)
    assert completed is not None
    assert completed.status == ScraperRunStatus.COMPLETED
    assert completed.total_rows == 1
    assert completed.output_json_path is None
    assert completed.output_excel_path is not None
    assert "canonical invalid" in (completed.error_message or "")


def test_fair_runner_scrape_exception_marks_failed(
    client, auth_headers, db_session, organization_id, user_id
):
    create_response = client.post(
        "/api/v1/fairs",
        json={
            "name": f"Fail Fair {uuid4().hex[:8]}",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
            "scraper_config": {"use_http": True},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    fair_id = UUID(create_response.json()["id"])

    def _boom(**_kwargs):
        raise RuntimeError("adapter crashed")

    mock_runner = FairScraperJobRunner(session_factory=lambda: db_session, scrape_executor=_boom)
    previous_runner = fairs_dependencies._fair_scraper_job_runner
    fairs_dependencies._fair_scraper_job_runner = mock_runner
    try:
        response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
    finally:
        fairs_dependencies._fair_scraper_job_runner = previous_runner
    assert response.status_code == 202
    run_id = UUID(response.json()["id"])
    mock_runner.run_fair_scraper(
        FairScraperJobCommand(
            run_id=run_id,
            organization_id=organization_id,
            fair_id=fair_id,
            user_id=user_id,
        )
    )
    db_session.expire_all()
    failed = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session)).get_run(run_id)
    assert failed is not None
    assert failed.status == ScraperRunStatus.FAILED
    assert failed.total_rows == 0
    assert "adapter crashed" in (failed.error_message or "")


def test_artifact_exception_does_not_rollback_completed_metrics(db_session, organization_id):
    """complete_run with handoff metrics must persist even when artifact paths are partial."""
    service = ScraperRunHistoryService(ScraperRunHistoryRepository(db_session))
    started = service.start_run(
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        organization_id=organization_id,
        input_url="https://example.test/list",
        fair_name="Metric Fair",
        fair_year=2026,
        run_source=ScraperRunSource.FAIR_AUTOMATION,
        started_at=datetime.now(UTC),
    )
    handoff = _sample_handoff(rows=3)
    bundle = ArtifactExportBundle(
        results=[
            ArtifactExportResult(key="json", path="/tmp/ok.json"),
            ArtifactExportResult(key="excel", error="xlsx writer failed"),
        ]
    )
    completed = service.complete_run(
        started.id,
        handoff=handoff,
        output_json_path=bundle.json_path,
        output_excel_path=bundle.excel_path,
        warning_message=bundle.warning_message(),
    )
    db_session.commit()
    assert completed.status == ScraperRunStatus.COMPLETED
    assert completed.total_rows == 3
    assert completed.output_json_path == "/tmp/ok.json"
    assert completed.output_excel_path is None
    assert completed.error_message is not None
    assert "xlsx writer failed" in completed.error_message
