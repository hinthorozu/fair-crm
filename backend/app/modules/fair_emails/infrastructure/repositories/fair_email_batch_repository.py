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
from app.modules.smtp.domain.smtp_timeout_errors import (
    SMTP_CONNECT_TIMEOUT_CODE,
    SMTP_TIMEOUT_CODE,
    timeout_log_message,
)

_TERMINAL_BATCH_STATUSES = frozenset(
    {"completed", "completed_with_errors", "failed", "cancelled"}
)
_SMTP_TIMEOUT_ERROR_CODES = frozenset({SMTP_CONNECT_TIMEOUT_CODE, SMTP_TIMEOUT_CODE})


class SqlAlchemyFairEmailBatchRepository(_LegacyFairEmailBatchRepository):
    """Repository with transaction-visible batch progress counters."""

    def update_outbox_sent(
        self,
        outbox_id: UUID,
        *,
        subject: str,
        body_html: str | None,
        body_text: str | None,
        external_message_id: str | None = None,
        provider_status: str | None = None,
    ) -> None:
        super().update_outbox_sent(
            outbox_id,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            external_message_id=external_message_id,
            provider_status=provider_status,
        )

    def update_outbox_failed(
        self,
        outbox_id: UUID,
        *,
        message: str,
        error_code: str | None = None,
    ) -> None:
        if error_code in _SMTP_TIMEOUT_ERROR_CODES:
            model = (
                self._session.query(FairEmailOutboxModel)
                .filter(FairEmailOutboxModel.id == outbox_id)
                .one()
            )
            self._append_log(
                model,
                error_code,
                timeout_log_message(error_code),
                datetime.now(timezone.utc),
            )
        super().update_outbox_failed(outbox_id, message=message, error_code=error_code)

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
