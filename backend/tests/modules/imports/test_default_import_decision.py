"""Default import row decision after analyze."""

from uuid import uuid4

from app.modules.imports.domain.entities import ImportRow
from app.modules.imports.domain.services.merge_preview import (
    assign_default_decision,
    default_decision_for_row,
)
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus


def _row(*, status: ImportRowStatus, match_customer_id=None):
    from datetime import UTC, datetime

    now = datetime.now(tz=UTC)
    return ImportRow.create(
        batch_id=uuid4(),
        organization_id=uuid4(),
        row_number=1,
        raw_data_json={"company_name": "Co"},
        normalized_data_json={"company_name": "Co"},
        status=status,
        validation_errors_json=None,
        match_customer_id=match_customer_id,
        match_confidence=100 if match_customer_id else None,
        match_reason="exact_normalized_match" if match_customer_id else None,
        now=now,
    )


def test_default_decision_update_when_match_present():
    customer_id = uuid4()
    row = _row(status=ImportRowStatus.READY_TO_UPDATE, match_customer_id=customer_id)
    assert default_decision_for_row(row) == ImportDecision.UPDATE_EXISTING


def test_default_decision_create_when_no_match():
    row = _row(status=ImportRowStatus.READY_TO_CREATE)
    assert default_decision_for_row(row) == ImportDecision.CREATE_NEW


def test_assign_default_decision_persists_on_row():
    from datetime import UTC, datetime

    customer_id = uuid4()
    row = _row(status=ImportRowStatus.READY_TO_UPDATE, match_customer_id=customer_id)
    now = datetime.now(tz=UTC)
    assign_default_decision(row, now=now)
    assert row.decision == ImportDecision.UPDATE_EXISTING
