"""Tenant-scoped live-progress repository for fair email batches.

The historical implementation remains in
``fair_email_batch_repository_legacy`` for compatibility, while this public
repository hardens every organization-owned batch/outbox mutation used by the
runtime. A batch or outbox identifier alone is never mutation authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, func

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
_PENDING_OUTBOX_STATUSES = ("queued", "pending", "sending")


class SqlAlchemyFairEmailBatchRepository(_LegacyFairEmailBatchRepository):
    """Repository whose public batch/outbox mutations fail closed by tenant."""

    def _get_scoped_outbox(
        self,
        organization_id: UUID,
        batch_id: UUID,
        outbox_id: UUID,
    ) -> FairEmailOutboxModel:
        return (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.id == outbox_id,
            )
            .one()
        )

    def _get_scoped_batch(
        self,
        organization_id: UUID,
        batch_id: UUID,
    ) -> FairEmailBatchModel:
        return (
            self._session.query(FairEmailBatchModel)
            .filter(
                FairEmailBatchModel.organization_id == organization_id,
                FairEmailBatchModel.id == batch_id,
            )
            .one()
        )

    def list_pending_outbox(
        self,
        organization_id: UUID,
        batch_id: UUID,
    ) -> list[FairEmailOutboxModel]:
        return (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.status.in_(_PENDING_OUTBOX_STATUSES),
            )
            .order_by(FairEmailOutboxModel.created_at.asc())
            .all()
        )

    def iter_pending_outbox(
        self,
        organization_id: UUID,
        batch_id: UUID,
        *,
        chunk_size: int,
    ):
        """Yield only tenant-owned pending rows, in bounded chunks."""
        size = max(1, chunk_size)
        while True:
            rows = (
                self._session.query(FairEmailOutboxModel)
                .filter(
                    FairEmailOutboxModel.organization_id == organization_id,
                    FairEmailOutboxModel.batch_id == batch_id,
                    FairEmailOutboxModel.status.in_(_PENDING_OUTBOX_STATUSES),
                )
                .order_by(FairEmailOutboxModel.created_at.asc())
                .limit(size)
                .all()
            )
            if not rows:
                return
            yield from rows

    def list_failed_outbox(
        self,
        organization_id: UUID,
        batch_id: UUID,
    ) -> list[FairEmailOutboxModel]:
        return (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.status == "failed",
            )
            .order_by(FairEmailOutboxModel.created_at.asc())
            .all()
        )

    def prepare_outbox_for_retry(
        self,
        organization_id: UUID,
        batch_id: UUID,
        outbox_id: UUID,
    ) -> None:
        now = datetime.now(timezone.utc)
        model = self._get_scoped_outbox(organization_id, batch_id, outbox_id)
        if model.status != "failed":
            raise ValueError("Only failed outbox items can be prepared for retry")
        model.send_attempt = int(model.send_attempt or 1) + 1
        model.status = "queued"
        model.error_message = None
        model.sent_at = None
        model.failed_at = None
        model.sending_started_at = None
        model.external_message_id = None
        model.provider_status = None
        model.scheduled_at = None
        model.updated_at = now
        self._append_log(model, "queued", "Mail retry kuyruğa alındı", now)
        self._refresh_batch_progress_for_outbox(
            organization_id,
            batch_id,
            outbox_id,
        )

    def mark_outbox_sending(
        self,
        organization_id: UUID,
        batch_id: UUID,
        outbox_id: UUID,
    ) -> None:
        now = datetime.now(timezone.utc)
        model = self._get_scoped_outbox(organization_id, batch_id, outbox_id)
        if not model.operation_logs:
            self._append_log(
                model,
                "queued",
                "Fuar toplu mail kuyruğa alındı",
                model.created_at or now,
            )
        model.status = "sending"
        model.sending_started_at = now
        model.updated_at = now
        self._append_log(model, "sending_started", "Fuar toplu mail gönderimi başladı", now)

    def fail_all_pending_outbox(
        self,
        organization_id: UUID,
        batch_id: UUID,
        *,
        message: str,
    ) -> int:
        now = datetime.now(timezone.utc)
        models = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.status.in_(_PENDING_OUTBOX_STATUSES),
            )
            .all()
        )
        for model in models:
            model.status = "failed"
            model.error_code = "batch_failure"
            model.error_message = message
            model.failed_at = now
            model.updated_at = now
            self._append_log(model, "failed", message, now)
        return len(models)

    def update_outbox_sent(
        self,
        organization_id: UUID,
        batch_id: UUID,
        outbox_id: UUID,
        *,
        subject: str,
        body_html: str | None,
        body_text: str | None,
        external_message_id: str | None = None,
        provider_status: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        model = self._get_scoped_outbox(organization_id, batch_id, outbox_id)
        model.status = "sent"
        model.rendered_subject = subject
        model.rendered_body_html = body_html
        model.rendered_body_text = body_text
        model.sent_at = now
        model.failed_at = None
        model.error_code = None
        model.error_message = None
        model.external_message_id = external_message_id
        model.provider_status = provider_status
        model.updated_at = now
        self._append_log(model, "sent", "Fuar toplu mail gönderildi", now)

    def update_outbox_failed(
        self,
        organization_id: UUID,
        batch_id: UUID,
        outbox_id: UUID,
        *,
        message: str,
        error_code: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        model = self._get_scoped_outbox(organization_id, batch_id, outbox_id)
        if error_code in _SMTP_TIMEOUT_ERROR_CODES:
            self._append_log(
                model,
                error_code,
                timeout_log_message(error_code),
                now,
            )
        model.status = "failed"
        model.error_code = error_code
        model.error_message = message
        model.failed_at = now
        model.updated_at = now
        self._append_log(model, "failed", message, now)

    def mark_batch_processing(
        self,
        organization_id: UUID,
        batch_id: UUID,
    ) -> None:
        now = datetime.now(timezone.utc)
        model = self._get_scoped_batch(organization_id, batch_id)
        model.status = "processing"
        model.updated_at = now

    def update_batch_counts(
        self,
        organization_id: UUID,
        batch_id: UUID,
        *,
        status: str,
        sent_count: int,
        failed_count: int,
    ) -> None:
        """Update live counts without allowing an ID-only batch mutation."""
        now = datetime.now(timezone.utc)
        model = self._get_scoped_batch(organization_id, batch_id)
        model.status = status
        model.sent_count = sent_count
        model.failed_count = failed_count
        model.updated_at = now
        model.completed_at = now if status in _TERMINAL_BATCH_STATUSES else None
        self._session.flush()

    def recount_batch_from_outbox(
        self,
        organization_id: UUID,
        batch_id: UUID,
    ) -> tuple[int, int, str]:
        """Return progress from outbox rows owned by the same organization and batch."""
        sent_count, failed_count, pending = (
            self._session.query(
                func.sum(case((FairEmailOutboxModel.status == "sent", 1), else_=0)),
                func.sum(case((FairEmailOutboxModel.status == "failed", 1), else_=0)),
                func.sum(
                    case(
                        (FairEmailOutboxModel.status.in_(_PENDING_OUTBOX_STATUSES), 1),
                        else_=0,
                    )
                ),
            )
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch_id,
            )
            .one()
        )
        sent_count = int(sent_count or 0)
        failed_count = int(failed_count or 0)
        pending = int(pending or 0)
        if pending > 0:
            status = "processing"
        elif failed_count == 0:
            status = "completed"
        else:
            status = "completed_with_errors"
        return sent_count, failed_count, status

    def link_operation(
        self,
        organization_id: UUID,
        batch_id: UUID,
        operation_id: UUID,
    ) -> None:
        model = self._get_scoped_batch(organization_id, batch_id)
        model.operation_id = operation_id
        model.updated_at = datetime.now(timezone.utc)

    def _refresh_batch_progress_for_outbox(
        self,
        organization_id: UUID,
        batch_id: UUID,
        outbox_id: UUID,
    ) -> None:
        # Re-load through the same scoped parent/child boundary before deriving progress.
        self._get_scoped_outbox(organization_id, batch_id, outbox_id)
        sent_count, failed_count, status = self.recount_batch_from_outbox(
            organization_id,
            batch_id,
        )
        self.update_batch_counts(
            organization_id,
            batch_id,
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
