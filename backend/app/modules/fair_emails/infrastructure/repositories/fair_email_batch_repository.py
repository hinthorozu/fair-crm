from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.fair_emails.domain.value_objects import RecipientOptions, ResolvedRecipient
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailBatchModel, FairEmailOutboxModel


@dataclass(frozen=True)
class FairEmailBatchRecord:
    id: UUID
    organization_id: UUID
    fair_id: UUID
    template_id: UUID
    smtp_account_id: UUID | None
    subject_override: str | None
    status: str
    total_count: int
    sent_count: int
    failed_count: int
    skipped_count: int


@dataclass(frozen=True)
class FairEmailBatchListRecord(FairEmailBatchRecord):
    created_at: datetime
    completed_at: datetime | None
    created_by_user_id: UUID


@dataclass(frozen=True)
class FairEmailOutboxItemRecord:
    id: UUID
    batch_id: UUID
    customer_id: UUID
    contact_id: UUID | None
    recipient_name: str | None
    company_name: str
    email: str
    source: str
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SqlAlchemyFairEmailBatchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_batch(
        self,
        *,
        organization_id: UUID,
        fair_id: UUID,
        template_id: UUID,
        smtp_account_id: UUID | None,
        subject_override: str | None,
        recipient_options: RecipientOptions,
        created_by_user_id: UUID,
        recipients: list[ResolvedRecipient],
    ) -> FairEmailBatchRecord:
        now = datetime.now(timezone.utc)
        batch_id = uuid4()
        will_send = [item for item in recipients if item.status == "will_send"]
        skipped = [item for item in recipients if item.status != "will_send"]

        batch = FairEmailBatchModel(
            id=batch_id,
            organization_id=organization_id,
            fair_id=fair_id,
            template_id=template_id,
            smtp_account_id=smtp_account_id,
            subject_override=subject_override,
            recipient_options_json={
                "include_customer_emails": recipient_options.include_customer_emails,
                "include_contact_emails": recipient_options.include_contact_emails,
                "skip_no_email": recipient_options.skip_no_email,
                "exclude_inactive": recipient_options.exclude_inactive,
                "dedupe_emails": recipient_options.dedupe_emails,
            },
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
            self._session.add(
                FairEmailOutboxModel(
                    id=uuid4(),
                    batch_id=batch_id,
                    organization_id=organization_id,
                    customer_id=item.customer_id,
                    contact_id=item.contact_id,
                    participation_id=item.participation_id,
                    recipient_name=item.recipient_name,
                    company_name=item.company_name,
                    email=item.email,
                    source=item.source,
                    status="pending",
                    skip_reason=None,
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
        models = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.organization_id == organization_id,
                FairEmailOutboxModel.batch_id == batch_id,
            )
            .order_by(FairEmailOutboxModel.created_at.asc())
            .all()
        )
        return [self._to_outbox_record(model) for model in models]

    def list_pending_outbox(self, batch_id: UUID) -> list[FairEmailOutboxModel]:
        return (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.status.in_(("pending", "sending")),
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
        model.status = "pending"
        model.error_message = None
        model.sent_at = None
        model.updated_at = now

    def mark_outbox_sending(self, outbox_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        model = self._session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
        model.status = "sending"
        model.updated_at = now

    def fail_all_pending_outbox(self, batch_id: UUID, *, message: str) -> int:
        now = datetime.now(timezone.utc)
        models = (
            self._session.query(FairEmailOutboxModel)
            .filter(
                FairEmailOutboxModel.batch_id == batch_id,
                FairEmailOutboxModel.status.in_(("pending", "sending")),
            )
            .all()
        )
        for model in models:
            model.status = "failed"
            model.error_message = message
            model.updated_at = now
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

    def update_outbox_failed(self, outbox_id: UUID, *, message: str) -> None:
        now = datetime.now(timezone.utc)
        model = self._session.query(FairEmailOutboxModel).filter(FairEmailOutboxModel.id == outbox_id).one()
        model.status = "failed"
        model.error_message = message
        model.updated_at = now

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

    @staticmethod
    def _to_record(model: FairEmailBatchModel) -> FairEmailBatchRecord:
        return FairEmailBatchRecord(
            id=model.id,
            organization_id=model.organization_id,
            fair_id=model.fair_id,
            template_id=model.template_id,
            smtp_account_id=model.smtp_account_id,
            subject_override=model.subject_override,
            status=model.status,
            total_count=model.total_count,
            sent_count=model.sent_count,
            failed_count=model.failed_count,
            skipped_count=model.skipped_count,
        )

    @staticmethod
    def _to_list_record(model: FairEmailBatchModel) -> FairEmailBatchListRecord:
        return FairEmailBatchListRecord(
            id=model.id,
            organization_id=model.organization_id,
            fair_id=model.fair_id,
            template_id=model.template_id,
            smtp_account_id=model.smtp_account_id,
            subject_override=model.subject_override,
            status=model.status,
            total_count=model.total_count,
            sent_count=model.sent_count,
            failed_count=model.failed_count,
            skipped_count=model.skipped_count,
            created_at=model.created_at,
            completed_at=model.completed_at,
            created_by_user_id=model.created_by_user_id,
        )

    @staticmethod
    def _to_outbox_record(model: FairEmailOutboxModel) -> FairEmailOutboxItemRecord:
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
            updated_at=model.updated_at,
        )
