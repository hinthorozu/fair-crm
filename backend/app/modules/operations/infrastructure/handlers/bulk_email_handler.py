"""Bulk email Operation handler — orchestrates fair_emails batch/outbox pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import FairBulkEmailMailOperationSync
from app.modules.fair_emails.application.send_bulk_email_operation import (
    SendBulkEmailOperationCommand,
    SendBulkEmailOperationUseCase,
)
from app.modules.fair_emails.domain.value_objects import RecipientOptions
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.exceptions import InvalidOperationConfigError
from app.modules.operations.domain.handler import (
    HandlerExecutionContext,
    HandlerStartResult,
    HandlerValidationResult,
)
from app.modules.operations.domain.source_normalization import extract_source_ids
from app.modules.operations.domain.value_objects import (
    HandlerCapabilities,
    OperationType,
    RunStatus,
    SourceKind,
)
from app.modules.operations.infrastructure.handlers.bulk_email_operation_sync import (
    extract_batch_id,
    merge_result_payload,
)


@dataclass(frozen=True)
class BulkEmailBatchJobCommand:
    batch_id: UUID
    organization_id: UUID
    operation_id: UUID | None = None
    operation_run_id: UUID | None = None


def _parse_uuid(value: Any) -> UUID | None:
    if value is None or value == "":
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _recipient_options_from_config(type_config: dict[str, Any]) -> RecipientOptions:
    raw = type_config.get("recipient_options")
    if not isinstance(raw, dict):
        raw = {}
    return RecipientOptions(
        include_customer_emails=bool(raw.get("include_customer_emails", True)),
        include_contact_emails=bool(raw.get("include_contact_emails", True)),
        skip_no_email=bool(raw.get("skip_no_email", True)),
        exclude_inactive=bool(raw.get("exclude_inactive", True)),
        dedupe_emails=bool(raw.get("dedupe_emails", True)),
    )


class BulkEmailHandler:
    """Starts operations bulk-email runs via existing fair_emails infrastructure."""

    operation_type = OperationType.BULK_EMAIL

    def __init__(
        self,
        *,
        session: Session | None = None,
        send_use_case: SendBulkEmailOperationUseCase | None = None,
        batch_repository: SqlAlchemyFairEmailBatchRepository | None = None,
        mail_operation_sync: FairBulkEmailMailOperationSync | None = None,
        job_scheduler: Callable[[BulkEmailBatchJobCommand], None] | None = None,
    ) -> None:
        self._session = session
        self._send_use_case = send_use_case
        self._batch_repository = batch_repository
        self._mail_operation_sync = mail_operation_sync
        self._job_scheduler = job_scheduler

    @property
    def capabilities(self) -> HandlerCapabilities:
        return HandlerCapabilities(
            supports_pause=False,
            supports_resume=False,
            supports_retry=True,
            supports_schedule=False,
            supports_items=False,
        )

    def validate_create(
        self,
        *,
        source_kind: str,
        source_config: dict[str, Any],
        type_config: dict[str, Any],
        run_settings: dict[str, Any],
        organization_id: UUID | None = None,
    ) -> HandlerValidationResult:
        _ = run_settings
        _ = organization_id
        # Allow draft create with incomplete type_config; start validates strictly.
        has_bulk_fields = any(
            type_config.get(key)
            for key in ("template_id", "smtp_account_id", "subject", "subject_override", "source_type")
        )
        if not has_bulk_fields:
            return HandlerValidationResult.success()
        return self._validate_bulk_config(
            source_kind=source_kind,
            source_config=source_config,
            type_config=type_config,
        )

    def validate_start(self, *, operation: Operation) -> HandlerValidationResult:
        return self._validate_bulk_config(
            source_kind=operation.source_kind,
            source_config=operation.source_config,
            type_config=operation.type_config,
        )

    def _validate_bulk_config(
        self,
        *,
        source_kind: str,
        source_config: dict[str, Any],
        type_config: dict[str, Any],
    ) -> HandlerValidationResult:
        errors: list[str] = []

        template_id = _parse_uuid(type_config.get("template_id"))
        smtp_account_id = _parse_uuid(type_config.get("smtp_account_id"))
        subject = str(type_config.get("subject") or type_config.get("subject_override") or "").strip()
        source_type = str(type_config.get("source_type") or "").strip().lower()

        if template_id is None:
            errors.append("type_config.template_id is required")
        if smtp_account_id is None:
            errors.append("type_config.smtp_account_id is required")
        if not subject:
            errors.append("type_config.subject is required")
        if source_type not in {"manual", "fair_list"}:
            errors.append("type_config.source_type must be manual or fair_list")

        source_ids = extract_source_ids(source_config)
        if source_type == "fair_list":
            if source_kind != SourceKind.FAIR:
                errors.append("fair_list requires source_kind=fair")
            fair_ids = source_ids or [
                uid
                for uid in (_parse_uuid(item) for item in (type_config.get("fair_ids") or []))
                if uid is not None
            ]
            if len(fair_ids) < 1:
                errors.append("fair_list requires at least one fair in source_ids")
        elif source_type == "manual":
            if source_kind not in {SourceKind.MANUAL_SELECTION, SourceKind.NONE, SourceKind.IMPORT}:
                errors.append("manual requires source_kind=manual_selection or none")
            manual_emails = str(type_config.get("manual_emails") or "").strip()
            excel_tokens = type_config.get("excel_email_tokens") or []
            if not isinstance(excel_tokens, (list, tuple)):
                errors.append("type_config.excel_email_tokens must be a list")
                excel_tokens = []
            if not manual_emails and not excel_tokens:
                errors.append("manual requires manual_emails and/or excel_email_tokens")

        if errors:
            return HandlerValidationResult.failure(*errors)
        return HandlerValidationResult.success()

    def on_start(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        return self._start_send(operation=operation, run=run, context=context)

    def on_retry(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        _ = context
        if self._batch_repository is None or self._job_scheduler is None:
            raise InvalidOperationConfigError(
                "Bulk email repositories are required to retry bulk email operations"
            )

        batch = self._batch_repository.get_batch_by_operation_id(
            operation.organization_id,
            operation.id,
        )
        if batch is None:
            # Fall back to prior run payload
            prior_batch_id = None
            if operation.latest_run_id is not None and self._session is not None:
                from app.modules.operations.infrastructure.repositories.operation_run_repository import (
                    SqlAlchemyOperationRunRepository,
                )

                prior = SqlAlchemyOperationRunRepository(self._session).get_by_id(
                    operation.organization_id,
                    operation.latest_run_id,
                )
                prior_batch_id = extract_batch_id(prior)
            if prior_batch_id is not None:
                batch = self._batch_repository.get_batch(
                    operation.organization_id,
                    prior_batch_id,
                )
        if batch is None:
            raise InvalidOperationConfigError("No bulk email batch linked to this operation")

        failed = self._batch_repository.list_failed_outbox(batch.id)
        if not failed:
            raise InvalidOperationConfigError("No failed recipients to retry")

        mail_repo = (
            SqlAlchemyMailSendOperationRepository(self._session)
            if self._session is not None
            else None
        )
        for outbox in failed:
            self._batch_repository.prepare_outbox_for_retry(outbox.id)
            if mail_repo is not None and outbox.mail_send_operation_id is not None:
                try:
                    mail_repo.prepare_for_retry(
                        operation.organization_id,
                        outbox.mail_send_operation_id,
                    )
                except Exception:
                    # If mail op cannot be retried, clear link so ensure_operations recreates.
                    outbox.mail_send_operation_id = None

        if self._mail_operation_sync is not None:
            refreshed = self._batch_repository.get_batch(operation.organization_id, batch.id)
            if refreshed is not None:
                self._mail_operation_sync.ensure_operations_for_batch(
                    organization_id=operation.organization_id,
                    batch=refreshed,
                    default_subject=batch.subject_override or "Toplu mail",
                )

        result_payload = {
            "batch_id": str(batch.id),
            "retry_failed_only": True,
            "retried_count": len(failed),
            "fair_id": str(batch.fair_id) if batch.fair_id else None,
        }
        merge_result_payload(run, result_payload)

        self._job_scheduler(
            BulkEmailBatchJobCommand(
                batch_id=batch.id,
                organization_id=operation.organization_id,
                operation_id=operation.id,
                operation_run_id=run.id,
            )
        )

        return HandlerStartResult(
            run_status=RunStatus.RUNNING,
            total_items=len(failed),
            message=f"Retrying {len(failed)} failed recipient(s)",
            result_payload=result_payload,
        )

    def on_cancel(
        self,
        *,
        operation: Operation,
        run: OperationRun | None,
        context: HandlerExecutionContext | None = None,
    ) -> None:
        # Best-effort no-op: in-flight SMTP sends are not safely interruptible.
        _ = operation, run, context
        return

    def _start_send(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        if self._send_use_case is None or self._job_scheduler is None:
            raise InvalidOperationConfigError(
                "Bulk email send use case is required to start bulk email operations"
            )

        validation = self.validate_start(operation=operation)
        if not validation.ok:
            raise InvalidOperationConfigError("; ".join(validation.errors))

        type_config = dict(operation.type_config or {})
        source_type = str(type_config.get("source_type") or "").strip().lower()
        template_id = _parse_uuid(type_config.get("template_id"))
        smtp_account_id = _parse_uuid(type_config.get("smtp_account_id"))
        subject = str(type_config.get("subject") or type_config.get("subject_override") or "").strip()
        assert template_id is not None and smtp_account_id is not None

        source_ids = extract_source_ids(operation.source_config)
        fair_ids = source_ids
        if not fair_ids:
            fair_ids = [
                uid
                for uid in (_parse_uuid(item) for item in (type_config.get("fair_ids") or []))
                if uid is not None
            ]

        excel_tokens_raw = type_config.get("excel_email_tokens") or []
        excel_tokens = [str(item).strip() for item in excel_tokens_raw if str(item).strip()]

        result = self._send_use_case.execute(
            SendBulkEmailOperationCommand(
                organization_id=operation.organization_id,
                user_id=context.user_id,
                access_token=context.access_token,
                source_type=source_type,
                template_id=template_id,
                smtp_account_id=smtp_account_id,
                subject=subject,
                fair_ids=fair_ids if source_type == "fair_list" else None,
                manual_emails=str(type_config.get("manual_emails") or "") or None,
                excel_email_tokens=excel_tokens or None,
                country_filter=str(type_config.get("country_filter") or "").strip() or None,
                city_filter=str(type_config.get("city_filter") or "").strip() or None,
                company_name_contains=(
                    str(type_config.get("company_name_contains") or "").strip() or None
                ),
                recipient_options=_recipient_options_from_config(type_config),
                operation_id=operation.id,
            )
        )

        result_payload = {
            "batch_id": str(result.batch_id),
            "source_type": source_type,
            "total_count": result.total_count,
            "will_send_count": result.will_send_count,
            "skipped_count": result.skipped_count,
            "fair_ids": [str(item) for item in fair_ids] if source_type == "fair_list" else [],
        }
        merge_result_payload(run, result_payload)

        self._job_scheduler(
            BulkEmailBatchJobCommand(
                batch_id=result.batch_id,
                organization_id=operation.organization_id,
                operation_id=operation.id,
                operation_run_id=run.id,
            )
        )

        return HandlerStartResult(
            run_status=RunStatus.RUNNING,
            total_items=result.will_send_count,
            message=result.message,
            result_payload=result_payload,
        )
