"""Unit tests for analyze job start + organization lock."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.data_integration.application.start_import_analyze_job import (
    StartImportAnalyzeJobCommand,
    StartImportAnalyzeJobUseCase,
)
from app.modules.imports.domain.entities import ImportBatch
from app.modules.imports.domain.exceptions import ImportAnalyzeInProgressError
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportSourceType


def _batch(*, status: ImportBatchStatus) -> ImportBatch:
    now = datetime.now(tz=UTC)
    return ImportBatch(
        id=uuid4(),
        organization_id=uuid4(),
        fair_id=uuid4(),
        source_type=ImportSourceType.EXCEL,
        file_name="test.xlsx",
        status=status,
        total_rows=10,
        valid_rows=0,
        invalid_rows=0,
        duplicate_rows=0,
        created_rows=0,
        updated_rows=0,
        skipped_rows=0,
        created_participations=0,
        updated_participations=0,
        column_mapping_json={"mappings": {"company_name": {"type": "column_index", "value": 0}}},
        raw_preview_json={"total_rows": 10, "rows": []},
        has_header_row=True,
        header_mode=None,
        header_row_index=0,
        selected_sheet_name="Sheet1",
        stored_file_content=b"x",
        created_at=now,
        updated_at=now,
        completed_at=None,
        notes=None,
    )


def test_start_analyze_job_rejects_when_org_has_active_job():
    org_id = uuid4()
    batch = _batch(status=ImportBatchStatus.MAPPING_COMPLETED)
    batch.organization_id = org_id

    batch_repo = MagicMock()
    batch_repo.get_by_id.return_value = batch
    job_repo = MagicMock()
    job_repo.has_active_analyze_job.return_value = True
    job_repo.get_active_analyze_job_for_batch.return_value = None
    auth = MagicMock()
    auth.check_permission.return_value = True

    use_case = StartImportAnalyzeJobUseCase(batch_repo, job_repo, auth)
    with pytest.raises(ImportAnalyzeInProgressError):
        use_case.execute(
            StartImportAnalyzeJobCommand(
                organization_id=org_id,
                user_id=uuid4(),
                access_token="token",
                batch_id=batch.id,
            )
        )


def test_start_analyze_job_allows_decision_required_batch():
    org_id = uuid4()
    batch = _batch(status=ImportBatchStatus.DECISION_REQUIRED)
    batch.organization_id = org_id

    batch_repo = MagicMock()
    batch_repo.get_by_id.return_value = batch
    job_repo = MagicMock()
    job_repo.has_active_analyze_job.return_value = False
    job_repo.get_active_analyze_job_for_batch.return_value = None
    job_repo.add.side_effect = lambda job: job
    auth = MagicMock()
    auth.check_permission.return_value = True

    use_case = StartImportAnalyzeJobUseCase(batch_repo, job_repo, auth)
    result = use_case.execute(
        StartImportAnalyzeJobCommand(
            organization_id=org_id,
            user_id=uuid4(),
            access_token="token",
            batch_id=batch.id,
        )
    )
    assert result.batch_id == batch.id
    batch_repo.update.assert_called_once()
