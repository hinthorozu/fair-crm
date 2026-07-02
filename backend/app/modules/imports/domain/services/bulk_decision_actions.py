"""Shared bulk decision action matching — preview and apply."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.imports.domain.entities import ImportRow
from app.modules.imports.domain.services.merge_preview import row_matches_filter
from app.modules.imports.domain.value_objects import ImportDecision

BULK_DECISION_ACTIONS = frozenset(
    {
        "create_all_new",
        "link_all_existing",
        "update_all_duplicates",
        "skip_invalid",
    }
)

BULK_ACTION_FILTER: dict[str, str] = {
    "create_all_new": "new",
    "link_all_existing": "will_update",
    "update_all_duplicates": "duplicate",
    "skip_invalid": "invalid",
}

_ACTION_SUMMARY_LABELS: dict[str, str] = {
    "create_all_new": "yeni müşteri olarak işaretlenecek",
    "link_all_existing": "mevcut müşteriye bağlanacak",
    "update_all_duplicates": "duplicate olarak güncellenecek",
    "skip_invalid": "atlanacak",
}


@dataclass(frozen=True)
class BulkDecisionPreview:
    action_type: str
    affected_rows: int
    already_decided_rows: int
    summary: str


def row_matches_bulk_preview(row: ImportRow, action: str) -> bool:
    """Same row scope as the decision-screen filter for this bulk action."""
    filter_key = BULK_ACTION_FILTER.get(action)
    if filter_key is None:
        return False
    if not row_matches_filter(row, filter_key):
        return False
    if action in ("link_all_existing", "update_all_duplicates"):
        return bool(row.match_customer_id)
    return True


def decision_for_bulk_action(action: str) -> ImportDecision | None:
    if action == "create_all_new":
        return ImportDecision.CREATE_NEW
    if action in ("link_all_existing", "update_all_duplicates"):
        return ImportDecision.UPDATE_EXISTING
    if action == "skip_invalid":
        return ImportDecision.SKIP
    return None


def row_matches_bulk_action(row: ImportRow, action: str) -> bool:
    """Rows in scope that apply will handle (set or already match target decision)."""
    if not row_matches_bulk_preview(row, action):
        return False
    target = decision_for_bulk_action(action)
    if target is None:
        return False
    if row.decision is None:
        return True
    return row.decision == target


def preview_bulk_decision(rows: list[ImportRow], action: str) -> BulkDecisionPreview:
    in_scope = [row for row in rows if row_matches_bulk_preview(row, action)]
    pending = [row for row in in_scope if row.decision is None]
    target = decision_for_bulk_action(action)
    already = sum(1 for row in in_scope if row.decision is not None and row.decision == target)
    label = _ACTION_SUMMARY_LABELS.get(action, action)
    affected = len(in_scope)
    summary = f"{len(pending)} kayıt {label}."
    return BulkDecisionPreview(
        action_type=action,
        affected_rows=affected,
        already_decided_rows=already,
        summary=summary,
    )


def apply_bulk_decision_to_row(row: ImportRow, action: str) -> bool:
    if not row_matches_bulk_action(row, action):
        return False
    decision = decision_for_bulk_action(action)
    if decision is None:
        return False
    if row.decision == decision:
        return True
    if row.decision is not None:
        return False
    row.set_decision(decision, now=datetime.now(tz=UTC))
    return True
