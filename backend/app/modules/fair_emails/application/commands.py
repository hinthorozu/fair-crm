from dataclasses import dataclass
from uuid import UUID

from app.modules.fair_emails.domain.value_objects import RecipientOptions


@dataclass(frozen=True)
class PreviewRecipientsQuery:
    organization_id: UUID
    fair_id: UUID
    access_token: str
    user_id: UUID
    recipient_options: RecipientOptions


@dataclass(frozen=True)
class PreviewBulkEmailCommand:
    organization_id: UUID
    fair_id: UUID
    access_token: str
    user_id: UUID
    template_id: UUID
    sample_recipient_key: str | None
    subject_override: str | None
    recipient_options: RecipientOptions


@dataclass(frozen=True)
class SendBulkEmailCommand:
    organization_id: UUID
    fair_id: UUID
    access_token: str
    user_id: UUID
    template_id: UUID
    smtp_account_id: UUID | None
    subject_override: str | None
    recipient_options: RecipientOptions


@dataclass(frozen=True)
class ProcessBatchCommand:
    batch_id: UUID
    organization_id: UUID


@dataclass(frozen=True)
class ListFairEmailBatchesQuery:
    organization_id: UUID
    fair_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class GetFairEmailBatchDetailQuery:
    organization_id: UUID
    fair_id: UUID
    batch_id: UUID
    access_token: str
    user_id: UUID
