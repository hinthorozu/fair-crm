"""Bulk decision preview must align with decision-screen row filters."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.imports.domain.entities import ImportRow
from app.modules.imports.domain.services.bulk_decision_actions import (
    apply_bulk_decision_to_row,
    preview_bulk_decision,
    row_matches_bulk_action,
    row_matches_bulk_preview,
)
from app.modules.imports.domain.services.merge_preview import row_matches_filter
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus


def _row(*, status: ImportRowStatus, decision: ImportDecision | None = None, match_customer_id=None):
    now = datetime.now(tz=UTC)
    row = ImportRow.create(
        batch_id=uuid4(),
        organization_id=uuid4(),
        row_number=1,
        raw_data_json={},
        normalized_data_json={"company_name": "Acme"},
        status=status,
        validation_errors_json=None,
        match_customer_id=match_customer_id,
        match_confidence=None,
        match_reason=None,
        now=now,
    )
    if decision is not None:
        row.decision = decision
    return row


def test_create_all_new_preview_matches_new_filter():
    rows = [
        _row(status=ImportRowStatus.READY_TO_CREATE),
        _row(status=ImportRowStatus.READY_TO_CREATE),
        _row(status=ImportRowStatus.READY_TO_UPDATE, match_customer_id=uuid4()),
        _row(status=ImportRowStatus.INVALID),
    ]
    new_filter_count = sum(1 for row in rows if row_matches_filter(row, "new"))
    preview = preview_bulk_decision(rows, "create_all_new")

    assert new_filter_count == 2
    assert preview.affected_rows == 2
    assert preview.already_decided_rows == 0
    assert row_matches_bulk_action(rows[0], "create_all_new")


def test_create_all_new_preview_excludes_pre_decided_rows():
    rows = [
        _row(status=ImportRowStatus.READY_TO_CREATE, decision=ImportDecision.CREATE_NEW),
        _row(status=ImportRowStatus.READY_TO_CREATE),
    ]
    new_filter_count = sum(1 for row in rows if row_matches_filter(row, "new"))
    preview = preview_bulk_decision(rows, "create_all_new")

    assert new_filter_count == 2
    assert preview.affected_rows == 2
    assert preview.already_decided_rows == 1
    assert row_matches_bulk_action(rows[0], "create_all_new")
    assert row_matches_bulk_action(rows[1], "create_all_new")
    assert apply_bulk_decision_to_row(rows[0], "create_all_new")
    assert apply_bulk_decision_to_row(rows[1], "create_all_new")
    assert rows[1].decision == ImportDecision.CREATE_NEW


def test_analyze_rows_start_without_default_decision():
    row = _row(status=ImportRowStatus.READY_TO_CREATE)
    assert row.decision is None
    assert row_matches_bulk_preview(row, "create_all_new")
