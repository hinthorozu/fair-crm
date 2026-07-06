"""Process queued mail_send_operations in controlled worker batches."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import FairBulkEmailMailOperationSync
from app.modules.fair_emails.application.retry_fair_bulk_email_operation import (
    FairBulkEmailOperationRetryHandler,
)
from app.modules.mail_send_operations.application.mail_send_operation_dispatcher import (
    MailSendOperationDispatcher,
)
from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.domain.entities import MailSendOperationRecord
from app.modules.mail_send_operations.domain.value_objects import (
    MailSendOperationStatus,
    MailSendSourceType,
)
from app.modules.mail_send_operations.domain.worker_constants import WORKER_LOG_SENT
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MailSendOperationWorkerResult:
    recovered_stuck_count: int
    picked_count: int
    sent_count: int
    failed_count: int
    skipped_count: int


class ProcessMailSendOperationsWorker:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = SqlAlchemyMailSendOperationRepository(session)
        self._mail_service = MailSendOperationService(self._repository)
        self._dispatcher = MailSendOperationDispatcher(session)
        self._fair_bulk_handler = FairBulkEmailOperationRetryHandler(session)
        self._mail_operation_sync = FairBulkEmailMailOperationSync(session)

    def run(self) -> MailSendOperationWorkerResult:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        recovered = self._recover_stuck_sending(
            now=now,
            timeout_minutes=settings.mail_sending_timeout_minutes,
        )
        candidates = self._repository.list_queued_for_worker(
            max_batch_size=settings.mail_worker_max_batch_size,
            now=now,
        )
        sent_count = 0
        failed_count = 0
        skipped_count = 0

        for candidate in candidates:
            outcome = self._process_candidate(candidate, now=now)
            if outcome == "sent":
                sent_count += 1
            elif outcome == "failed":
                failed_count += 1
            else:
                skipped_count += 1

        self._session.flush()
        return MailSendOperationWorkerResult(
            recovered_stuck_count=recovered,
            picked_count=len(candidates),
            sent_count=sent_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
        )

    def _recover_stuck_sending(self, *, now: datetime, timeout_minutes: int) -> int:
        cutoff = now - timedelta(minutes=timeout_minutes)
        stuck_records = self._repository.list_stuck_sending(cutoff=cutoff)
        recovered = 0
        for record in stuck_records:
            self._mail_service.mark_sending_timeout_failed(
                record.organization_id,
                record.id,
                timeout_minutes=timeout_minutes,
            )
            self._sync_fair_bulk_failure(record, message="Gönderim zaman aşımına uğradı")
            recovered += 1
        return recovered

    def _process_candidate(
        self,
        candidate: MailSendOperationRecord,
        *,
        now: datetime,
    ) -> str:
        claimed = self._repository.try_claim_queued_operation(
            candidate.organization_id,
            candidate.id,
            now=now,
        )
        if claimed is None:
            return "skipped"

        self._mail_service.mark_worker_sending(claimed.organization_id, claimed.id)
        try:
            self._dispatcher.dispatch(claimed)
        except SmtpMailDeliveryError as exc:
            message = exc.args[0] if exc.args else "Mail gönderimi başarısız oldu."
            self._mail_service.mark_failed(
                claimed.organization_id,
                claimed.id,
                error_code=exc.error_type,
                error_message=message,
            )
            self._sync_fair_bulk_failure(claimed, message=message, error_code=exc.error_type)
            return "failed"
        except Exception as exc:
            message = str(exc).strip() or "Mail gönderimi başarısız oldu."
            self._mail_service.mark_failed(
                claimed.organization_id,
                claimed.id,
                error_code=type(exc).__name__,
                error_message=message,
            )
            self._sync_fair_bulk_failure(claimed, message=message, error_code=type(exc).__name__)
            logger.exception(
                "mail_worker_operation_failed operation_id=%s organization_id=%s",
                claimed.id,
                claimed.organization_id,
            )
            return "failed"

        if claimed.source_type == MailSendSourceType.FAIR_BULK_EMAIL:
            outbox = self._fair_bulk_handler.get_outbox_for_operation(
                claimed.organization_id,
                claimed.id,
            )
            if outbox is not None:
                self._mail_operation_sync.sync_outbox_sent(
                    claimed.organization_id,
                    outbox,
                    subject=outbox.rendered_subject or claimed.subject,
                    body_html=outbox.rendered_body_html,
                    body_text=outbox.rendered_body_text,
                )
            return "sent"

        self._mail_service.mark_sent(
            claimed.organization_id,
            claimed.id,
            log_message=WORKER_LOG_SENT,
        )
        return "sent"

    def _sync_fair_bulk_failure(
        self,
        operation: MailSendOperationRecord,
        *,
        message: str,
        error_code: str | None = None,
    ) -> None:
        if operation.source_type != MailSendSourceType.FAIR_BULK_EMAIL:
            return
        outbox = self._fair_bulk_handler.get_outbox_for_operation(
            operation.organization_id,
            operation.id,
        )
        if outbox is None:
            return
        self._fair_bulk_handler.sync_outbox_failed(outbox.id, message=message)
        refreshed = self._repository.get_by_id(operation.organization_id, operation.id)
        if refreshed is not None and refreshed.status == MailSendOperationStatus.FAILED:
            return
        self._mail_operation_sync.sync_outbox_failed(
            operation.organization_id,
            outbox,
            error_code=error_code,
            error_message=message,
        )


def process_mail_send_operations(session: Session) -> MailSendOperationWorkerResult:
    return ProcessMailSendOperationsWorker(session).run()
