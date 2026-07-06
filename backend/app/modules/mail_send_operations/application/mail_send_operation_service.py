from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.modules.mail_send_operations.domain.value_objects import MailSendOperationStatus, MailSendSourceType
from app.modules.mail_send_operations.domain.worker_constants import (
    SENDING_TIMEOUT_ERROR_CODE,
    WORKER_LOG_SENDING_TIMEOUT,
    WORKER_LOG_SENDING_TIMEOUT_FAILED,
)
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    CreateMailSendOperationParams,
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.smtp.domain.exceptions import SmtpMailDeliveryError
from app.modules.smtp.domain.smtp_timeout_errors import (
    SMTP_CONNECT_TIMEOUT_CODE,
    SMTP_TIMEOUT_CODE,
    timeout_log_message,
)

SMTP_TIMEOUT_ERROR_CODES = frozenset({SMTP_CONNECT_TIMEOUT_CODE, SMTP_TIMEOUT_CODE})
WORKER_FAILURE_ERROR_CODES = SMTP_TIMEOUT_ERROR_CODES | {SENDING_TIMEOUT_ERROR_CODE}


class MailSendOperationService:
    def __init__(self, repository: SqlAlchemyMailSendOperationRepository) -> None:
        self._repository = repository

    def create_mail_send_operation(self, params: CreateMailSendOperationParams):
        operation = self._repository.create(params)
        return self._repository.append_operation_log(
            operation.organization_id,
            operation.id,
            event="queued",
            message="Mail kuyruğa alındı",
        )

    def mark_sending(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        log_message: str = "Gönderim başladı",
    ):
        operation = self._repository.mark_sending(organization_id, operation_id)
        return self._repository.append_operation_log(
            organization_id,
            operation_id,
            event="sending_started",
            message=log_message,
        )

    def mark_sent(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        log_message: str = "Mail başarıyla gönderildi",
    ):
        operation = self._repository.mark_sent(organization_id, operation_id)
        return self._repository.append_operation_log(
            organization_id,
            operation_id,
            event="sent",
            message=log_message,
        )

    def mark_failed(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        error_code: str | None,
        error_message: str | None,
        log_message: str | None = None,
    ):
        if error_code in WORKER_FAILURE_ERROR_CODES:
            event = error_code
            if error_code == SENDING_TIMEOUT_ERROR_CODE:
                message = WORKER_LOG_SENDING_TIMEOUT
            else:
                message = timeout_log_message(error_code)
            self._repository.append_operation_log_once(
                organization_id,
                operation_id,
                event=event,
                message=message,
            )
        operation = self._repository.mark_failed(
            organization_id,
            operation_id,
            error_code=error_code,
            error_message=error_message,
        )
        return self._repository.append_operation_log(
            organization_id,
            operation_id,
            event="failed",
            message=log_message or error_message or "Mail gönderimi başarısız oldu",
        )

    def mark_cancelled(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        message: str | None = None,
    ):
        operation = self._repository.mark_cancelled(
            organization_id,
            operation_id,
            error_message=message,
        )
        return self._repository.append_operation_log(
            organization_id,
            operation_id,
            event="cancelled",
            message=message or "Mail operasyonu iptal edildi",
        )

    def append_operation_log(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        event: str,
        message: str,
    ):
        return self._repository.append_operation_log(
            organization_id,
            operation_id,
            event=event,
            message=message,
        )

    def append_operation_log_once(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        event: str,
        message: str,
    ):
        return self._repository.append_operation_log_once(
            organization_id,
            operation_id,
            event=event,
            message=message,
        )

    def mark_worker_sending(
        self,
        organization_id: UUID,
        operation_id: UUID,
    ):
        self._repository.append_operation_log_once(
            organization_id,
            operation_id,
            event="picked_by_worker",
            message="Worker tarafından seçildi",
        )
        operation = self._repository.get_by_id(organization_id, operation_id)
        if operation is None:
            return None
        if operation.status == MailSendOperationStatus.SENDING:
            return self._repository.append_operation_log_once(
                organization_id,
                operation_id,
                event="sending_started",
                message="Worker gönderimi başladı",
            )
        return self.mark_sending(
            organization_id,
            operation_id,
            log_message="Worker gönderimi başladı",
        )

    def mark_sending_timeout_failed(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        timeout_minutes: int,
    ):
        message = (
            f"{WORKER_LOG_SENDING_TIMEOUT_FAILED} "
            f"(eşik: {timeout_minutes} dakika)"
        )
        return self.mark_failed(
            organization_id,
            operation_id,
            error_code=SENDING_TIMEOUT_ERROR_CODE,
            error_message=message,
            log_message=message,
        )

    def execute_synchronous_send(
        self,
        params: CreateMailSendOperationParams,
        *,
        send_fn: Callable[[], None],
    ) -> UUID:
        operation = self.create_mail_send_operation(params)
        self.mark_sending(operation.organization_id, operation.id)
        try:
            send_fn()
        except SmtpMailDeliveryError as exc:
            message = exc.args[0] if exc.args else "SMTP gönderimi başarısız oldu."
            self.mark_failed(
                operation.organization_id,
                operation.id,
                error_code=exc.error_type,
                error_message=message,
            )
            raise
        except Exception as exc:
            self.mark_failed(
                operation.organization_id,
                operation.id,
                error_code=type(exc).__name__,
                error_message=str(exc).strip() or "Mail gönderimi başarısız oldu.",
            )
            raise
        self.mark_sent(operation.organization_id, operation.id)
        return operation.id

    def execute_retry_synchronous(
        self,
        organization_id: UUID,
        operation_id: UUID,
        *,
        send_fn: Callable[[], None],
    ):
        self.append_operation_log(
            organization_id,
            operation_id,
            event="retry_requested",
            message="Retry requested by admin",
        )
        self._repository.prepare_for_retry(organization_id, operation_id)
        self.append_operation_log(
            organization_id,
            operation_id,
            event="queued",
            message="Mail retry kuyruğa alındı",
        )
        self.mark_sending(
            organization_id,
            operation_id,
            log_message="Retry gönderimi başladı",
        )
        try:
            send_fn()
        except SmtpMailDeliveryError as exc:
            message = exc.args[0] if exc.args else "SMTP gönderimi başarısız oldu."
            self.mark_failed(
                organization_id,
                operation_id,
                error_code=exc.error_type,
                error_message=message,
            )
            raise
        except Exception as exc:
            self.mark_failed(
                organization_id,
                operation_id,
                error_code=type(exc).__name__,
                error_message=str(exc).strip() or "Mail gönderimi başarısız oldu.",
            )
            raise
        return self.mark_sent(
            organization_id,
            operation_id,
            log_message="Retry başarılı",
        )

    def create_consent_skipped_operation(
        self,
        params: CreateMailSendOperationParams,
        *,
        error_code: str,
        error_message: str,
    ):
        return self._repository.create_consent_skipped(
            params,
            error_code=error_code,
            error_message=error_message,
        )

    def record_immediate_failure(
        self,
        params: CreateMailSendOperationParams,
        *,
        error_code: str | None,
        error_message: str,
    ) -> UUID:
        operation = self._repository.create_immediate_failure(
            params,
            error_code=error_code,
            error_message=error_message,
        )
        return operation.id
