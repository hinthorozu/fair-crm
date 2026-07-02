"""Unit tests for decision filter matching and counts."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.services.merge_preview import (
    compute_decision_filter_counts,
    row_matches_filter,
)
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus


def _row(*, status: ImportRowStatus, decision: ImportDecision | None = None) -> ImportRow:
    now = datetime.now(tz=UTC)
    return ImportRow(
        id=uuid4(),
        batch_id=uuid4(),
        organization_id=uuid4(),
        row_number=1,
        raw_data_json={},
        normalized_data_json={"company_name": "Test"},
        status=status,
        validation_errors_json=None,
        match_customer_id=None,
        match_confidence=None,
        match_reason=None,
        participation_exists=None,
        match_participation_id=None,
        suggested_action=None,
        decision=decision,
        created_customer_id=None,
        updated_customer_id=None,
        created_participation_id=None,
        updated_participation_id=None,
        created_at=now,
        updated_at=now,
    )


def _batch(*, created_rows=0, updated_rows=0, skipped_rows=0) -> ImportBatch:
    now = datetime.now(tz=UTC)
    batch = ImportBatch.create(
        organization_id=uuid4(),
        fair_id=uuid4(),
        file_name="test.xlsx",
        now=now,
    )
    batch.created_rows = created_rows
    batch.updated_rows = updated_rows
    batch.skipped_rows = skipped_rows
    return batch


def test_skip_filter_matches_rows_with_skip_decision():
    pending_skip = _row(status=ImportRowStatus.INVALID, decision=ImportDecision.SKIP)
    assert row_matches_filter(pending_skip, "skip")


def test_applied_filter_never_matches_remaining_rows():
    row = _row(status=ImportRowStatus.READY_TO_CREATE)
    assert not row_matches_filter(row, "applied")


def test_compute_decision_filter_counts():
    rows = [
        _row(status=ImportRowStatus.READY_TO_CREATE),
        _row(status=ImportRowStatus.INVALID),
        _row(status=ImportRowStatus.INVALID, decision=ImportDecision.SKIP),
    ]
    batch = _batch(created_rows=2, skipped_rows=1)
    counts = compute_decision_filter_counts(rows, batch=batch)
    assert counts["all"] == 3
    assert counts["pending"] == 3
    assert counts["applied"] == 3
    assert counts["new"] == 1
    assert counts["invalid"] == 2
    assert counts["skip"] == 1
