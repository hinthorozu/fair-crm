"""Live-progress extension for the fair email batch repository.

The original repository implementation is preserved in
``fair_email_batch_repository_legacy``. This module keeps the public import
path stable while updating batch counters whenever an outbox row reaches or
leaves a terminal state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.modules.fair_emails.infrastructure.persistence.models import (
    FairEmailBatchModel,
    FairEmailOutboxModel,
)
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository_legacy import (
    FairEmailBatchListRecord,
    FairEmailBatchRecord,
    FairEmailOutboxItemRecord,
    SqlAlchemyFairEmailBatchRepository as _LegacyFairEmailBatchRepository,
)

_TERMINAL_BATCH_STATUSES = frozenset(
    {"completed", "completed_with_errors", "failed", "cancelled"}
)


class SqlAlchemyFairEmailBatchRepository(_LegacyFairEmailBatchRepository):
    """Repository with transaction-visible batch progress counters."""

    def update_outbox_sent(
        self,
        outbox_id: UUID,
        *,
        subject: str,
        body_html: str | None,
        body_text: str | None,
    ) -> None:
        super().update_outbox_sent(
            outbox_id,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )
        self._refresh_batch_progress_for_outbox(outbox_id)

    def update_outbox_failed(self, outbox_id: UUID, *, message: str) -> None:
        super().update_outbox_failed(outbox_id, message=message)
        self._refresh_batch_progress_for_outbox(outbox_id)

    def prepare_outbox_for_retry(self, outbox_id: UUID) -> None:
        super().prepare_outbox_for_retry(outbox_id)
        self._refresh_batch_progress_for_outbox(outbox_id)

    def update_batch_counts(
        self,
        batch_id: UUID,
        *,
        status: str,
        sent_count: int,
        failed_count: int,
    ) -> None:
        """Update live counts without marking an in-flight batch completed."""
        now = datetime.now(timezone.utc)
        model = (
            self._session.query(FairEmailBatchModel)
            .filter(FairEmailBatchModel.id == batch_id)
            .one()
        )
        model.status = status
        model.sent_count = sent_count
        model.failed_count = failed_count
        model.updated_at = now
        model.completed_at = now if status in _TERMINAL_BATCH_STATUSES else None
        self._session.flush()

    def _refresh_batch_progress_for_outbox(self, outbox_id: UUID) -> None:
        outbox = (
            self._session.query(FairEmailOutboxModel)
            .filter(FairEmailOutboxModel.id == outbox_id)
            .one()
        )
        sent_count, failed_count, status = self.recount_batch_from_outbox(outbox.batch_id)
        self.update_batch_counts(
            outbox.batch_id,
            status=status,
            sent_count=sent_count,
            failed_count=failed_count,
        )


__all__ = [
    "FairEmailBatchListRecord",
    "FairEmailBatchRecord",
    "FairEmailOutboxItemRecord",
    "SqlAlchemyFairEmailBatchRepository",
]
