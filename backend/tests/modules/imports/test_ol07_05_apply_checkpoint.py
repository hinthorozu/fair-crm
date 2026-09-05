from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

from app.modules.imports.application.apply_import import ApplyImportUseCase, RowApplyCounters
from app.modules.imports.application.lifecycle_aware_apply_import import LifecycleAwareApplyImportUseCase


def test_lifecycle_aware_apply_checks_before_row_mutation(monkeypatch):
    order: list[str] = []

    def checkpoint() -> None:
        order.append("checkpoint")

    def base_finalize(self, batch, row, command, now):
        order.append("apply")
        return RowApplyCounters(applied=True)

    monkeypatch.setattr(ApplyImportUseCase, "finalize_applied_row", base_finalize)
    use_case = object.__new__(LifecycleAwareApplyImportUseCase)
    use_case._progress_checkpoint = checkpoint

    result = use_case.finalize_applied_row(
        Mock(),
        Mock(),
        Mock(),
        datetime.now(tz=UTC),
    )

    assert result.applied is True
    assert order == ["checkpoint", "apply"]
