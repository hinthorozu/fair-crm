"""Unit tests for scraper ↔ operation run status mapping."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.modules.operations.domain.entities import OperationRun
from app.modules.operations.domain.value_objects import RunStatus
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import (
    apply_scraper_progress_to_run,
    extract_scraper_run_id,
    map_scraper_status_to_run_status,
    merge_result_payload,
)
from app.modules.scraper.domain.scraper_run_history import ScraperRunStatus


def test_merge_and_extract_scraper_run_id():
    run = OperationRun.create(
        organization_id=uuid4(),
        operation_id=uuid4(),
        now=datetime.now(tz=UTC),
        triggered_by=uuid4(),
        status=RunStatus.RUNNING,
    )
    scraper_run_id = uuid4()
    merge_result_payload(
        run,
        {"scraper_run_id": str(scraper_run_id), "import_batch_id": None},
    )
    assert extract_scraper_run_id(run) == scraper_run_id


def test_map_scraper_status_to_run_status():
    assert map_scraper_status_to_run_status(ScraperRunStatus.RUNNING) == RunStatus.RUNNING
    assert map_scraper_status_to_run_status(ScraperRunStatus.COMPLETED) == RunStatus.COMPLETED
    assert map_scraper_status_to_run_status(ScraperRunStatus.FAILED) == RunStatus.FAILED
    assert map_scraper_status_to_run_status(ScraperRunStatus.CANCELLED) == RunStatus.CANCELLED
    assert map_scraper_status_to_run_status(ScraperRunStatus.CANCEL_REQUESTED) == RunStatus.RUNNING


def test_apply_scraper_progress_updates_counts_and_import_batch():
    run = OperationRun.create(
        organization_id=uuid4(),
        operation_id=uuid4(),
        now=datetime.now(tz=UTC),
        triggered_by=uuid4(),
        status=RunStatus.RUNNING,
    )
    batch_id = uuid4()
    scraper_run = SimpleNamespace(
        id=uuid4(),
        adapter_key="tuyap_new",
        fair_id=uuid4(),
        progress_total=10,
        progress_current=4,
        total_rows=0,
        import_batch_id=batch_id,
        input_url="https://example.com/list",
        status=ScraperRunStatus.RUNNING,
        error_message=None,
    )
    apply_scraper_progress_to_run(run, scraper_run)
    assert run.total_items == 10
    assert run.processed_items == 4
    result = (run.error_details or {}).get("result") or {}
    assert result["import_batch_id"] == str(batch_id)
    assert result["adapter_key"] == "tuyap_new"
