from uuid import UUID

from pydantic import BaseModel, Field


class RecipientOptionsRequest(BaseModel):
    include_customer_emails: bool = True
    include_contact_emails: bool = True
    skip_no_email: bool = True
    exclude_inactive: bool = True
    dedupe_emails: bool = True


class PreviewRecipientsRequest(BaseModel):
    recipient_options: RecipientOptionsRequest = Field(default_factory=RecipientOptionsRequest)


class RecipientPreviewItemResponse(BaseModel):
    recipient_key: str
    recipient_name: str | None
    company_name: str
    email: str
    source: str
    customer_id: UUID
    contact_id: UUID | None
    participation_id: UUID
    status: str
    skip_reason: str | None


class RecipientPreviewSummaryResponse(BaseModel):
    total_customers: int
    total_contacts: int
    valid_email_count: int
    deduped_recipient_count: int
    skipped_count: int
    recipients: list[RecipientPreviewItemResponse]


class PreviewBulkEmailRequest(BaseModel):
    template_id: UUID
    sample_recipient_key: str | None = None
    subject_override: str | None = None
    recipient_options: RecipientOptionsRequest = Field(default_factory=RecipientOptionsRequest)


class BulkEmailContentPreviewResponse(BaseModel):
    subject: str
    body_html: str | None
    body_text: str | None
    sample_recipient: RecipientPreviewItemResponse
    total_send_count: int


class SendBulkEmailRequest(BaseModel):
    template_id: UUID
    smtp_account_id: UUID | None = None
    subject_override: str | None = None
    recipient_options: RecipientOptionsRequest = Field(default_factory=RecipientOptionsRequest)


class SendBulkEmailResponse(BaseModel):
    batch_id: UUID
    status: str
    total_count: int
    skipped_count: int
    message: str


class ErrorResponse(BaseModel):
    detail: str


class FairEmailBatchListItemResponse(BaseModel):
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
    created_at: str
    completed_at: str | None


class FairEmailBatchListResponse(BaseModel):
    items: list[FairEmailBatchListItemResponse]


class FairEmailBatchDetailResponse(BaseModel):
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
    created_at: str
    completed_at: str | None
    created_by_user_id: UUID


class FairEmailOutboxItemResponse(BaseModel):
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
    sent_at: str | None
    created_at: str
    updated_at: str


class FairEmailBatchDetailEnvelopeResponse(BaseModel):
    batch: FairEmailBatchDetailResponse
    items: list[FairEmailOutboxItemResponse]
