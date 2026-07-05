from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fair_emails.application.commands import GetFairEmailBatchDetailQuery
from app.modules.fair_emails.application.preview_recipients import PERMISSION_PREVIEW
from app.modules.fair_emails.domain.exceptions import (
    FairBulkEmailBatchNotFoundError,
    FairNotEligibleForBulkEmailError,
)
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    FairEmailBatchListRecord,
    FairEmailOutboxItemRecord,
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.mail_templates.domain.ports import MailTemplateRepository
from app.modules.smtp.domain.ports import SmtpAccountRepository


@dataclass(frozen=True)
class FairEmailBatchDetail:
    id: UUID
    fair_id: UUID
    status: str
    template_id: UUID
    template_name: str | None
    smtp_account_id: UUID | None
    smtp_account_name: str | None
    subject: str | None
    subject_override: str | None
    total_recipients: int
    queued_count: int
    sent_count: int
    failed_count: int
    skipped_count: int
    created_at: datetime
    completed_at: datetime | None
    created_by_user_id: UUID


@dataclass(frozen=True)
class FairEmailOutboxDetailItem:
    id: UUID
    recipient_email: str
    recipient_name: str | None
    company_name: str
    recipient_source: str
    customer_id: UUID
    contact_id: UUID | None
    status: str
    error_message: str | None
    attempts: int
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FairEmailBatchDetailResult:
    batch: FairEmailBatchDetail
    items: list[FairEmailOutboxDetailItem]


class GetFairEmailBatchDetailUseCase:
    def __init__(
        self,
        fair_repository: FairRepository,
        batch_repository: SqlAlchemyFairEmailBatchRepository,
        template_repository: MailTemplateRepository,
        smtp_repository: SmtpAccountRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._fair_repository = fair_repository
        self._batch_repository = batch_repository
        self._template_repository = template_repository
        self._smtp_repository = smtp_repository
        self._authorization = authorization

    def execute(self, query: GetFairEmailBatchDetailQuery) -> FairEmailBatchDetailResult:
        if not self._authorization.check_permission(
            organization_id=query.organization_id,
            user_id=query.user_id,
            permission_code=PERMISSION_PREVIEW,
            access_token=query.access_token,
        ):
            raise ForbiddenError("Permission denied")

        fair = self._fair_repository.get_by_id(query.organization_id, query.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")
        if fair.deleted_at is not None:
            raise FairNotEligibleForBulkEmailError("Arşivlenmiş fuar için toplu mail gönderilemez.")

        batch = self._batch_repository.get_batch_for_fair(
            query.organization_id,
            query.fair_id,
            query.batch_id,
        )
        if batch is None:
            raise FairBulkEmailBatchNotFoundError("Batch not found")

        outbox_items = self._batch_repository.list_outbox_for_batch(query.organization_id, batch.id)
        return FairEmailBatchDetailResult(
            batch=self._to_batch_detail(query.organization_id, batch),
            items=[self._to_outbox_item(item) for item in outbox_items],
        )

    def _to_batch_detail(self, organization_id: UUID, batch: FairEmailBatchListRecord) -> FairEmailBatchDetail:
        template = self._template_repository.get_by_id(organization_id, batch.template_id)
        template_name = template.name if template is not None else None
        subject = batch.subject_override or (template.subject if template is not None else None)

        smtp_name = None
        if batch.smtp_account_id is not None:
            account = self._smtp_repository.get_by_id(organization_id, batch.smtp_account_id)
            smtp_name = account.name if account is not None else None

        queued_count = max(0, batch.total_count - batch.sent_count - batch.failed_count)
        return FairEmailBatchDetail(
            id=batch.id,
            fair_id=batch.fair_id,
            status=batch.status,
            template_id=batch.template_id,
            template_name=template_name,
            smtp_account_id=batch.smtp_account_id,
            smtp_account_name=smtp_name,
            subject=subject,
            subject_override=batch.subject_override,
            total_recipients=batch.total_count,
            queued_count=queued_count,
            sent_count=batch.sent_count,
            failed_count=batch.failed_count,
            skipped_count=batch.skipped_count,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
            created_by_user_id=batch.created_by_user_id,
        )

    @staticmethod
    def _to_outbox_item(item: FairEmailOutboxItemRecord) -> FairEmailOutboxDetailItem:
        status = item.status
        if status == "pending":
            status = "queued"

        attempts = 1 if status in {"sent", "failed"} else 0
        return FairEmailOutboxDetailItem(
            id=item.id,
            recipient_email=item.email,
            recipient_name=item.recipient_name,
            company_name=item.company_name,
            recipient_source=item.source,
            customer_id=item.customer_id,
            contact_id=item.contact_id,
            status=status,
            error_message=item.error_message,
            attempts=attempts,
            sent_at=item.sent_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
