from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.fair_emails.domain.value_objects import RecipientOptions, ResolvedRecipient
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailBatchModel, FairEmailOutboxModel


@dataclass(frozen=True)
class FairEmailBatchRecord:
    id: UUID
    organization_id: UUID
    fair_id: UUID | None
    template_id: UUID
    email_account_id: UUID | None
    subject_override: str | None
    status: str
    total_count: int
    sent_count: int
    failed_count: int
    skipped_count: int
    operation_id: UUID | None
    created_at: datetime


@dataclass(frozen=True)
class FairEmailBatchListRecord(FairEmailBatchRecord):
    completed_at: datetime | None
    created_by_user_id: UUID


@dataclass(frozen=True)
class FairEmailOutboxItemRecord:
    id: UUID
    batch_id: UUID
    customer_id: UUID | None
    contact_id: UUID | None
    recipient_name: str | None
    company_name: str
    email: str
    source: str
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    send_attempt: int = 1
    participation_id: UUID | None = None
    fair_name: str | None = None
    external_message_id: str | None = None
    provider_status: str | None = None


class SqlAlchemyFairEmailBatchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_batch(
        self,
        *,
        organization_id: UUID,
        fair_id: UUID | None,
        template_id: UUID,
        email_account_id: UUID | None,
        subject_override: str | None,
        recipient_options: RecipientOptions,
        created_by_user_id: UUID,
        recipients: list[ResolvedRecipient],
        operation_id: UUID | None = None,
        recipient_options_extra: dict | None = None,
    ) -> FairEmailBatchRecord:
        from app.shared.email import is_valid_email_address

        now = datetime.now(timezone.utc)
        batch_id = uuid4()
        # Defense: never enqueue structurally invalid addresses even if status is wrong.
        will_send = [
            item
            for item in recipients
            if item.status == "will_send"
            and is_valid_email_address((item.email or "").strip())
        ]
        will_send_keys = {item.recipient_key for item in will_send}
        skipped = [item for item in recipients if item.recipient_key not in will_send_keys]

        options_json: dict = {
            "include_customer_emails": recipient_options.include_customer_emails,
            "include_contact_emails": recipient_options.include_contact_emails,
            "skip_no_email": recipient_options.skip_no_email,
            "exclude_inactive": recipient_options.exclude_inactive,
            "dedupe_emails": recipient_options.dedupe_emails,
        }
        if recipient_options_extra:
            options_json.update(recipient_options_extra)

        batch = FairEmailBatchModel(
            id=batch_id,
            organization_id=organization_id,
            fair_id=fair_id,
            operation_id=operation_id,
            template_id=template_id,
            email_account_id=email_account_id,
            subject_override=subject_override,
            recipient_options_json=options_json,
            status="queued",
            total_count=len(will_send),
            sent_count=0,
            failed_count=0,
            skipped_count=len(skipped),
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(batch)

        for item in will_send:
            company_name = (item.company_name or "").strip() or item.email
            self._session.add(
                FairEmailOutboxModel(
                    id=uuid4(),
                    source_type="fair_bulk_email",
                    priority=99,
                    batch_id=batch_id,
                    organization_id=organization_id,
                    customer_id=item.customer_id,
                    contact_id=item.contact_id,
                    participation_id=item.participation_id,
                    recipient_name=item.recipient_name,
                    company_name=company_name,
                    email=item.email,
                    source=item.source,
                    fair_name=item.fair_name,
                    status="queued",
                    subject=subject_override or "Toplu e-posta",
                    email_account_id=email_account_id,
                    template_id=template_id,
                    fair_id=fair_id,
                    skip_reason=None,
                    send_attempt=1,
                    max_retry_count=3,
                    operation_logs=[
                        {
                            "time": now.isoformat().replace("+00:00", "Z"),
                            "event": "queued",
                            "message": "Fuar toplu mail kuyruğa alındı",
                        }
                    ],
                    metadata_json={},
                    queued_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )

        self._session.flush()
        return self._to_record(batch)

    def get_batch(self, organization_id: UUID, batch_id: UUID) -> FairEmailBatchRecord | None:
        model = (
            self._session.query(FairEmailBatchModel)
            .filter(
                FairEmailBatchModel.organization_id == organization_id,
                FairEmailBatchModel.id == batch_id,
            )
            .one_or_none()
        )
        return self._to_record(model) if model else None

    def get_batch_by_operation_id(
        self,
        organization_id: UUID,
        operation_id: UUID,
    ) -> FairEmailBatchRecord | None:
        model = (
            self._session.query(FairEmailBatchModel)
            .filter(
                FairEmailBatchModel.organization_id == organization_id,
                FairEmailBatchModel.operation_id == operation_id,
            )
            .order_by(FairEmailBatchModel.created_at.desc())
            .first()
        )
        return self._to_record(model) if model else None

    def get_batch_for_fair(
        self,
        organization_id: UUID,
        fair_id: UUID,
        batch_id: UUID,
    ) -> FairEmailBatchListRecord | None:
        model = (
            self._session.query(FairEmailBatchModel)
            .filter(
                FairEmailBatchModel.organization_id == organization_id,
                FairEmailBatchModel.fair_id == fair_id,
                FairEmailBatchModel.id == batch_id,
            )
            .one_or_none()
        )
        return self._to_list_record(model) if model else None

    def list_batches_for_fair(self, organization_id: UUID, fair_id: UUID) -> list[FairEmailBatchListRecord]:
        models = (
            self._session.query(FairEmailBatchModel)
            .filter(
                FairEmailBatchModel.organization_id == organization_id,
                FairEmailBatchModel.fair_id == fair_id,
            )
            .order_by(FairEmailBatchModel.created_at.desc())
            .all()
        )
        return [self._to_list_record(model) for model in models]

    def list_outbox_for_batch(self, organization_id: UUID, batch_id: UUID) -> list[FairEmailOutboxItemRecord]:
        rows = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch_id,
            )
            .order_by(FairEmailOutboxModel.created_at.asc())
            .all()
        )
        return [
            self._to_outbox_record(
                outbox,
                external_message_id=outbox.external_message_id,
                provider_status=outbox.provider_status,
                updated_at=outbox.updated_at,
            )
            for outbox in rows
        ]

    def list_recent_outbox_for_batch(
        self,
        organization_id: UUID,
        batch_id: UUID,
        *,
        limit: int = 200,
    ) -> list[FairEmailOutboxItemRecord]:
        """Return only the most recently updated rows needed by the live log."""
        rows = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch_id,
            )
            .order_by(FairEmailOutboxModel.updated_at.desc(), FairEmailOutboxModel.created_at.desc())
            .limit(max(1, limit))
            .all()
        )
        rows.reverse()
        return [
            self._to_outbox_record(
                outbox,
                external_message_id=outbox.external_message_id,
                provider_status=outbox.provider_status,
                updated_at=outbox.updated_at,
            )
            for outbox in rows
        ]

    def list_outbox_page_for_batch(
        self,
        organization_id: UUID,
        batch_id: UUID,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        status: str | None = None,
        provider_status: str | None = None,
    ) -> tuple[list[FairEmailOutboxItemRecord], int]:
        """Return one filtered recipient page without loading the whole batch."""
        query = self._session.query(FairEmailOutboxModel).filter(
            FairEmailOutboxModel.organization_id == organization_id,
            FairEmailOutboxModel.batch_id == batch_id,
        )
        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    FairEmailOutboxModel.recipient_email.ilike(pattern),
                    FairEmailOutboxModel.recipient_name.ilike(pattern),
                    FairEmailOutboxModel.company_name.ilike(pattern),
                    FairEmailOutboxModel.fair_name.ilike(pattern),
                    FairEmailOutboxModel.recipient_source.ilike(pattern),
                )
            )
        if status:
            query = query.filter(FairEmailOutboxModel.status == status)
        if provider_status:
            query = query.filter(FairEmailOutboxModel.provider_status == provider_status)

        total = query.count()
        rows = (
            query.order_by(FairEmailOutboxModel.created_at.asc())
            .offset((max(1, page) - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return (
            [
                self._to_outbox_record(
                    outbox,
                    external_message_id=outbox.external_message_id,
                    provider_status=outbox.provider_status,
                    updated_at=outbox.updated_at,
                )
                for outbox in rows
            ],
            total,
        )

    def list_pending_outbox(self, batch_id: UUID) -> list[FairEmailOutboxModel]:
        return (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.status.in_(("queued", "pending", "sending")),
            )
            .order_by(FairEmailOutboxModel.created_at.asc())
            .all()
        )

    def iter_pending_outbox(
        self,
        batch_id: UUID,
        *,
        chunk_size: int,
    ):
        """Yield pending rows while loading at most ``chunk_size`` rows at once."""
        size = max(1, chunk_size)
        while True:
            rows = (
                self._session.query(FairEmailOutboxModel)
                .filter(
                    FairEmailOutboxModel.batch_id == batch_id,
                    FairEmailOutboxModel.status.in_(("queued", "pending", "sending")),
                )
                .order_by(FairEmailOutboxModel.created_at.asc())
                .limit(size)
                .all()
            )
            if not rows:
                return
            yield from rows

    def list_failed_outbox(self, batch_id: UUID) -> list[FairEmailOutboxModel]:
        return (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.status == "failed",
            )
            .order_by(FairEmailOutboxModel.created_at.asc())
            .all()
        )

    def get_outbox_by_mail_send_operation_id(
        self,
        organization_id: UUID,
        mail_send_operation_id: UUID,
    ) -> FairEmailOutboxModel | None:
        return (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.mail_send_operation_id == mail_send_operation_id,
            )
            .one_or_none()
        )

    def prepare_outbox_for_retry(self, outbox_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        model = self._session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
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

    def mark_outbox_sending(self, outbox_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        model = self._session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
        if not model.operation_logs:
            self._append_log(model, "queued", "Fuar toplu mail kuyruğa alındı", model.created_at or now)
        model.status = "sending"
        model.sending_started_at = now
        model.updated_at = now
        self._append_log(model, "sending_started", "Fuar toplu mail gönderimi başladı", now)

    def fail_all_pending_outbox(self, batch_id: UUID, *, message: str) -> int:
        now = datetime.now(timezone.utc)
        models = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.status.in_(("queued", "pending", "sending")),
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

    def update_outbox_sent(self, outbox_id: UUID, *, subject: str, body_html: str | None, body_text: str | None) -> None:
        now = datetime.now(timezone.utc)
        model = self._session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
        model.status = "sent"
        model.rendered_subject = subject
        model.rendered_body_html = body_html
        model.rendered_body_text = body_text
        model.sent_at = now
        model.updated_at = now
        self._append_log(model, "sent", "Fuar toplu mail gönderildi", now)

    def update_outbox_failed(
        self,
        outbox_id: UUID,
        *,
        message: str,
        error_code: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        model = self._session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
        model.status = "failed"
        model.error_code = error_code
        model.error_message = message
        model.failed_at = now
        model.updated_at = now
        self._append_log(model, "failed", message, now)

    def mark_batch_processing(self, batch_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        model = self._session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
        model.status = "processing"
        model.updated_at = now

    def update_batch_counts(
        self,
        batch_id: UUID,
        *,
        status: str,
        sent_count: int,
        failed_count: int,
    ) -> None:
        now = datetime.now(timezone.utc)
        model = self._session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
        model.status = status
        model.sent_count = sent_count
        model.failed_count = failed_count
        model.updated_at = now
        model.completed_at = now

    def recount_batch_from_outbox(self, batch_id: UUID) -> tuple[int, int, str]:
        """Return (sent_count, failed_count, status) based on current outbox rows."""
        models = (
            self._session.query(FairEmailOutboxModel)
            .filter(FairEmailOutboxModel.batch_id == batch_id)
            .all()
        )
        sent_count = sum(1 for item in models if item.status == "sent")
        failed_count = sum(1 for item in models if item.status == "failed")
        pending = sum(1 for item in models if item.status in ("queued", "pending", "sending"))
        if pending > 0:
            status = "processing"
        elif failed_count == 0:
            status = "completed"
        else:
            # Match historical process_batch semantics: any failures → completed_with_errors
            # (including all-failed). Explicit batch abort paths still set status="failed".
            status = "completed_with_errors"
        return sent_count, failed_count, status

    def link_operation(self, batch_id: UUID, operation_id: UUID) -> None:
        model = self._session.query(FairEmailBatchModel).filter(FairEmailBatchModel.id == batch_id).one()
        model.operation_id = operation_id
        model.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _to_record(model: FairEmailBatchModel) -> FairEmailBatchRecord:
        return FairEmailBatchRecord(
            id=model.id,
            organization_id=model.organization_id,
            fair_id=model.fair_id,
            template_id=model.template_id,
            email_account_id=model.email_account_id,
            subject_override=model.subject_override,
            status=model.status,
            total_count=model.total_count,
            sent_count=model.sent_count,
            failed_count=model.failed_count,
            skipped_count=model.skipped_count,
            operation_id=model.operation_id,
            created_at=model.created_at,
        )

    @staticmethod
    def _to_list_record(model: FairEmailBatchModel) -> FairEmailBatchListRecord:
        return FairEmailBatchListRecord(
            id=model.id,
            organization_id=model.organization_id,
            fair_id=model.fair_id,
            template_id=model.template_id,
            email_account_id=model.email_account_id,
            subject_override=model.subject_override,
            status=model.status,
            total_count=model.total_count,
            sent_count=model.sent_count,
            failed_count=model.failed_count,
            skipped_count=model.skipped_count,
            operation_id=model.operation_id,
            created_at=model.created_at,
            completed_at=model.completed_at,
            created_by_user_id=model.created_by_user_id,
        )

    @staticmethod
    def _to_outbox_record(
        model: FairEmailOutboxModel,
        *,
        external_message_id: str | None = None,
        provider_status: str | None = None,
        updated_at: datetime | None = None,
    ) -> FairEmailOutboxItemRecord:
        return FairEmailOutboxItemRecord(
            id=model.id,
            batch_id=model.batch_id,
            customer_id=model.customer_id,
            contact_id=model.contact_id,
            recipient_name=model.recipient_name,
            company_name=model.company_name,
            email=model.email,
            source=model.source,
            status=model.status,
            error_message=model.error_message,
            sent_at=model.sent_at,
            created_at=model.created_at,
            updated_at=updated_at,
            send_attempt=int(model.send_attempt or 1),
            participation_id=model.participation_id,
            fair_name=model.fair_name,
            external_message_id=external_message_id,
            provider_status=provider_status,
        )

    @staticmethod
    def _append_log(model: FairEmailOutboxModel, event: str, message: str, at: datetime) -> None:
        logs = list(model.operation_logs or [])
        logs.append(
            {
                "time": at.isoformat().replace("+00:00", "Z"),
                "event": event,
                "message": message,
            }
        )
        model.operation_logs = logs
