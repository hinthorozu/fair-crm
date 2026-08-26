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
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
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
from app.modules.email_delivery.domain.results import EmailDeliveryResult
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError

logger = logging.getLogger(__name__)


def _provider_fields_from_delivery_result(
    result: EmailDeliveryResult | None,
) -> tuple[str | None, str | None]:
    if not isinstance(result, EmailDeliveryResult):
        return None, None
    return result.external_message_id, result.provider_status


@dataclass(frozen=True)
class MailSendOperationWorkerResult:
    recovered_stuck_count: int
    picked_count: int
    sent_count: int
    failed_count: int
    skipped_count: int
    retried_count: int = 0


class ProcessMailSendOperationsWorker:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = SqlAlchemyMailSendOperationRepository(session)
        self._mail_service = MailSendOperationService(self._repository)
        self._dispatcher = MailSendOperationDispatcher(session)
        self._batch_repository = SqlAlchemyFairEmailBatchRepository(session)
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
        retried_count = 0

        for candidate in candidates:
            outcome = self._process_candidate(candidate, now=now)
            if outcome == "sent":
                sent_count += 1
            elif outcome == "failed":
                failed_count += 1
            elif outcome == "retried":
                retried_count += 1
            else:
                skipped_count += 1
            self._session.commit()

        self._sync_fair_batch_progress(candidates)

        if not candidates:
            retry_candidates = self._repository.list_failed_for_auto_retry(
                max_batch_size=settings.mail_worker_max_batch_size,
                now=now,
            )
            for candidate in retry_candidates:
                self._repository.requeue_for_auto_retry(
                    candidate.organization_id,
                    candidate.id,
                )
                retried_count += 1
            if retry_candidates:
                self._sync_fair_batch_progress(retry_candidates)
                self._session.commit()
            else:
                # A service restart can happen after the last recipient commit
                # but before batch/run counters are finalized. Reconcile those
                # non-terminal batches while the queue is idle.
                self._reconcile_nonterminal_fair_batches()
                self._session.commit()

        self._session.flush()
        return MailSendOperationWorkerResult(
            recovered_stuck_count=recovered,
            picked_count=len(candidates),
            sent_count=sent_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            retried_count=retried_count,
        )

    def _sync_fair_batch_progress(
        self,
        records: list[MailSendOperationRecord],
    ) -> None:
        batch_keys = {
            (record.organization_id, record.batch_id)
            for record in records
            if record.source_type == MailSendSourceType.FAIR_BULK_EMAIL
            and record.batch_id is not None
        }
        for organization_id, batch_id in batch_keys:
            sent_count, failed_count, status = self._batch_repository.recount_batch_from_outbox(
                organization_id,
                batch_id,
            )
            self._batch_repository.update_batch_counts(
                organization_id,
                batch_id,
                status=status,
                sent_count=sent_count,
                failed_count=failed_count,
            )
            batch = self._batch_repository.get_batch(organization_id, batch_id)
            if batch is None or batch.operation_id is None:
                continue
            from app.modules.operations.infrastructure.handlers.bulk_email_operation_sync import (
                sync_operation_run_from_batch,
            )

            sync_operation_run_from_batch(
                self._session,
                organization_id=organization_id,
                operation_id=batch.operation_id,
                batch=batch,
            )

    def _reconcile_nonterminal_fair_batches(self) -> None:
        for organization_id, batch_id in self._batch_repository.list_nonterminal_batch_keys():
            sent_count, failed_count, status = self._batch_repository.recount_batch_from_outbox(
                organization_id,
                batch_id,
            )
            self._batch_repository.update_batch_counts(
                organization_id,
                batch_id,
                status=status,
                sent_count=sent_count,
                failed_count=failed_count,
            )
            batch = self._batch_repository.get_batch(organization_id, batch_id)
            if batch is None or batch.operation_id is None:
                continue
            from app.modules.operations.infrastructure.handlers.bulk_email_operation_sync import (
                sync_operation_run_from_batch,
            )

            sync_operation_run_from_batch(
                self._session,
                organization_id=organization_id,
                operation_id=batch.operation_id,
                batch=batch,
            )

    def _recover_stuck_sending(self, *, now: datetime, timeout_minutes: int) -> int:
        cutoff = now - timedelta(minutes=timeout_minutes)
        stuck_records = self._repository.list_stuck_sending(
            cutoff=cutoff,
        )
        recovered = 0
        for record in stuck_records:
            self._mail_service.mark_sending_timeout_failed(
                record.organization_id,
                record.id,
                timeout_minutes=timeout_minutes,
            )
            # Keep error_code token in outbox message so UI can flag uncertain delivery.
            self._sync_fair_bulk_failure(
                record,
                message=(
                    f"sending_timeout: Gönderim zaman aşımına uğradı "
                    f"(eşik: {timeout_minutes} dakika). "
                    "SMTP maili kabul etmiş olabilir; sonuç belirsiz."
                ),
                error_code="sending_timeout",
            )
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
        delivery_result: EmailDeliveryResult | None = None
        try:
            delivery_result = self._dispatcher.dispatch(claimed)
        except SmtpMailDeliveryError as exc:
            message = exc.args[0] if exc.args else "Mail gönderimi başarısız oldu."
            self._mail_service.mark_failed(
                claimed.organization_id,
                claimed.id,
                error_code=exc.error_type,
                error_message=message,
                provider_status=getattr(exc, "provider_status", None),
            )
            if exc.retryable is not None:
                self._repository.set_auto_retry_pending(
                    claimed.organization_id,
                    claimed.id,
                    enabled=exc.retryable,
                )
            if exc.retry_after_seconds is not None and exc.retry_after_seconds > 0:
                self._repository.set_retry_not_before(
                    claimed.organization_id,
                    claimed.id,
                    scheduled_at=now + timedelta(seconds=exc.retry_after_seconds),
                )
            self._sync_fair_bulk_failure(claimed, message=message, error_code=exc.error_type)
            return "failed"
        except Exception as exc:
            message = str(exc).strip() or "Mail gönderimi başarısız oldu."
            error_code = type(exc).__name__
            self._mail_service.mark_failed(
                claimed.organization_id,
                claimed.id,
                error_code=error_code,
                error_message=message,
            )
            self._sync_fair_bulk_failure(claimed, message=message, error_code=error_code)
            logger.exception(
                "mail_worker_operation_failed operation_id=%s organization_id=%s",
                claimed.id,
                claimed.organization_id,
            )
            return "failed"

        external_message_id, provider_status = _provider_fields_from_delivery_result(delivery_result)

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
                    external_message_id=external_message_id,
                    provider_status=provider_status,
                )
            return "sent"

        self._mail_service.mark_sent(
            claimed.organization_id,
            claimed.id,
            log_message=WORKER_LOG_SENT,
            external_message_id=external_message_id,
            provider_status=provider_status,
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
        if outbox is None or outbox.batch_id is None:
            return
        self._fair_bulk_handler.sync_outbox_failed(
            operation.organization_id,
            outbox.batch_id,
            outbox.id,
            message=message,
        )
        self._dispatcher.record_fair_bulk_terminal_activity(operation)
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


# Optional override for tests (same pattern as fair bulk batch processor).
_mail_worker_session_factory = None


def configure_mail_worker_session_factory(factory) -> None:
    global _mail_worker_session_factory
    _mail_worker_session_factory = factory


def set_mail_worker_session_factory(factory) -> None:
    """Backward-compatible alias used by tests."""
    configure_mail_worker_session_factory(factory)


def process_mail_send_operations_background(*, max_drain_rounds: int = 100) -> MailSendOperationWorkerResult:
    """Background entry: open a fresh session and drain queued mail operations.

    Used after enqueue paths (e.g. manual_task_mail) so records do not stay
    ``queued`` until a manual CLI worker run. Safe to call when the queue is empty.
    """
    from app.db.session import SessionLocal

    session_factory = _mail_worker_session_factory or SessionLocal
    session = session_factory()
    recovered = 0
    picked = 0
    sent = 0
    failed = 0
    skipped = 0
    retried = 0
    try:
        logger.info("mail_worker_background_started")
        for round_index in range(max(1, max_drain_rounds)):
            result = process_mail_send_operations(session)
            session.commit()
            recovered += result.recovered_stuck_count
            picked += result.picked_count
            sent += result.sent_count
            failed += result.failed_count
            skipped += result.skipped_count
            retried += result.retried_count
            if result.picked_count == 0:
                break
            logger.info(
                "mail_worker_background_round round=%s picked=%s sent=%s failed=%s retried=%s",
                round_index + 1,
                result.picked_count,
                result.sent_count,
                result.failed_count,
                result.retried_count,
            )
        logger.info(
            "mail_worker_background_completed recovered=%s picked=%s sent=%s failed=%s skipped=%s retried=%s",
            recovered,
            picked,
            sent,
            failed,
            skipped,
            retried,
        )
        return MailSendOperationWorkerResult(
            recovered_stuck_count=recovered,
            picked_count=picked,
            sent_count=sent,
            failed_count=failed,
            skipped_count=skipped,
            retried_count=retried,
        )
    except Exception:
        session.rollback()
        logger.exception("mail_worker_background_failed")
        raise
    finally:
        if _mail_worker_session_factory is None:
            session.close()
