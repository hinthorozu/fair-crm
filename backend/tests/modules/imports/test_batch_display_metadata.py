"""Tests for import batch display metadata resolution."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.imports.application.batch_display_metadata import (
    resolve_adapter_key_from_batch,
    resolve_adapter_key_from_batch_preview,
    resolve_adapter_key_from_file_name,
)
from app.modules.imports.domain.entities import ImportBatch
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportSourceType


def _batch(
    *,
    file_name: str = "test.xlsx",
    raw_preview_json: dict | None = None,
    source_type: ImportSourceType = ImportSourceType.SCRAPER,
) -> ImportBatch:
    now = datetime.now(tz=UTC)
    return ImportBatch(
        id=uuid4(),
        organization_id=uuid4(),
        fair_id=None,
        source_type=source_type,
        file_name=file_name,
        status=ImportBatchStatus.RECEIVED,
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        duplicate_rows=0,
        created_rows=0,
        updated_rows=0,
        skipped_rows=0,
        created_participations=0,
        updated_participations=0,
        column_mapping_json=None,
        raw_preview_json=raw_preview_json,
        has_header_row=None,
        header_mode=None,
        header_row_index=None,
        selected_sheet_name=None,
        stored_file_content=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
        notes=None,
    )


def test_resolve_adapter_key_from_batch_preview():
    preview = {"canonical_source": {"adapter_key": "tuyap_old"}}
    assert resolve_adapter_key_from_batch_preview(preview) == "tuyap_old"


def test_resolve_adapter_key_from_file_name_scraper_pattern():
    run_id = "b4a64e3c-e74b-4ee0-a021-368ecfeb6f1a"
    assert resolve_adapter_key_from_file_name(f"tuyap_old-{run_id}.json") == "tuyap_old"


def test_resolve_adapter_key_from_file_name_excel_returns_none():
    assert resolve_adapter_key_from_file_name("customers.xlsx") is None


def test_resolve_adapter_key_from_batch_prefers_raw_preview():
    batch = _batch(
        file_name="tuyap_old-b4a64e3c-e74b-4ee0-a021-368ecfeb6f1a.json",
        raw_preview_json={"canonical_source": {"adapter_key": "tuyap_new"}},
    )
    assert resolve_adapter_key_from_batch(batch) == "tuyap_new"


def test_resolve_adapter_key_from_batch_falls_back_to_file_name():
    run_id = str(uuid4())
    batch = _batch(
        file_name=f"tuyap_old-{run_id}.json",
        raw_preview_json=None,
    )
    assert resolve_adapter_key_from_batch(batch) == "tuyap_old"


def test_resolve_adapter_key_from_batch_excel_returns_none():
    batch = _batch(file_name="import.xlsx", source_type=ImportSourceType.EXCEL)
    assert resolve_adapter_key_from_batch(batch) is None
