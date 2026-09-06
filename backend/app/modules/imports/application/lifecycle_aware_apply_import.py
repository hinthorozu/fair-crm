"""OL07-05 row-boundary lifecycle wrapper for import apply."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.modules.imports.application.apply_import import ApplyImportUseCase, RowApplyCounters
from app.modules.imports.application.commands import ApplyImportCommand
from app.modules.imports.domain.entities import ImportBatch, ImportRow


class LifecycleAwareApplyImportUseCase(ApplyImportUseCase):
    """Check lifecycle before every independently applied import row.

    The enclosing background runner owns the transaction.  If a checkpoint
    raises, the current transaction is rolled back before the job is
    terminalized, so no partially applied row set is committed.
    """

    def __init__(
        self,
        *args: Any,
        progress_checkpoint: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._progress_checkpoint = progress_checkpoint

    def finalize_applied_row(
        self,
        batch: ImportBatch,
        row: ImportRow,
        command: ApplyImportCommand,
        now: datetime,
    ) -> RowApplyCounters:
        if self._progress_checkpoint is not None:
            self._progress_checkpoint()
        return super().finalize_applied_row(batch, row, command, now)
