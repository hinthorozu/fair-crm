"""Successful apply removes import rows from the decision queue."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.commands import ApplyImportCommand
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.services.bulk_decision_actions import apply_bulk_decision_to_row
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus


def _invalid_row() -> ImportRow:
    now = datetime.now(tz=UTC)
    return ImportRow.create(
        batch_id=uuid4(),
        organization_id=uuid4(),
        row_number=2,
        raw_data_json={},
        normalized_data_json={"company_name": ""},
        status=ImportRowStatus.INVALID,
        validation_errors_json=["invalid_company_name"],
        match_customer_id=None,
        match_confidence=None,
        match_reason=None,
        now=now,
    )


def _batch(org_id, batch_id) -> ImportBatch:
    now = datetime.now(tz=UTC)
    batch = ImportBatch.create(
        organization_id=org_id,
        fair_id=uuid4(),
        file_name="test.xlsx",
        now=now,
    )
    batch.id = batch_id
    return batch


def test_finalize_applied_row_deletes_invalid_skip_row():
    row = _invalid_row()
    assert apply_bulk_decision_to_row(row, "skip_invalid")
    assert row.decision == ImportDecision.SKIP

    org_id = row.organization_id
    batch = _batch(org_id, row.batch_id)
    row_repo = MagicMock()
    use_case = ApplyImportUseCase(
        MagicMock(),
        row_repo,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    command = ApplyImportCommand(
        organization_id=org_id,
        user_id=uuid4(),
        access_token="token",
        batch_id=batch.id,
    )
    now = datetime.now(tz=UTC)

    counters = use_case.finalize_applied_row(batch, row, command, now)

    assert counters.skipped == 1
    assert counters.applied is True
    row_repo.delete_many.assert_called_once_with(org_id, batch.id, [row.id])
    assert batch.skipped_rows == 1
