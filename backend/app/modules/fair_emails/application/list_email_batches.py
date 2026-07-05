from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fair_emails.application.commands import ListFairEmailBatchesQuery
from app.modules.fair_emails.application.preview_recipients import PERMISSION_PREVIEW
from app.modules.fair_emails.domain.exceptions import FairNotEligibleForBulkEmailError
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    FairEmailBatchListRecord,
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.mail_templates.domain.ports import MailTemplateRepository
from app.modules.smtp.domain.ports import SmtpAccountRepository


@dataclass(frozen=True)
class FairEmailBatchListItem:
    id: UUID
    status: str
    template_id: UUID
    template_name: str | None
    smtp_account_id: UUID | None
    smtp_account_name: str | None
    subject: str | None
    total_recipients: int
    queued_count: int
    sent_count: int
    failed_count: int
    skipped_count: int
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class FairEmailBatchListResult:
    items: list[FairEmailBatchListItem]


class ListFairEmailBatchesUseCase:
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

    def execute(self, query: ListFairEmailBatchesQuery) -> FairEmailBatchListResult:
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

        batches = self._batch_repository.list_batches_for_fair(query.organization_id, query.fair_id)
        return FairEmailBatchListResult(
            items=[self._to_list_item(query.organization_id, batch) for batch in batches],
        )

    def _to_list_item(self, organization_id: UUID, batch: FairEmailBatchListRecord) -> FairEmailBatchListItem:
        template = self._template_repository.get_by_id(organization_id, batch.template_id)
        template_name = template.name if template is not None else None
        subject = batch.subject_override or (template.subject if template is not None else None)

        smtp_name = None
        if batch.smtp_account_id is not None:
            account = self._smtp_repository.get_by_id(organization_id, batch.smtp_account_id)
            smtp_name = account.name if account is not None else None

        queued_count = max(0, batch.total_count - batch.sent_count - batch.failed_count)
        return FairEmailBatchListItem(
            id=batch.id,
            status=batch.status,
            template_id=batch.template_id,
            template_name=template_name,
            smtp_account_id=batch.smtp_account_id,
            smtp_account_name=smtp_name,
            subject=subject,
            total_recipients=batch.total_count,
            queued_count=queued_count,
            sent_count=batch.sent_count,
            failed_count=batch.failed_count,
            skipped_count=batch.skipped_count,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
        )
