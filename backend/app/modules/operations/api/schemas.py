from typing import Any, Literal, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse

OperationTypeField = Literal[
    "scraper",
    "email",
    "bulk_email",
    "enrichment",
    "duplicate_check",
    "data_cleanup",
    "whatsapp",
    "manual_task",
    "reminder",
]

OperationStatusField = Literal[
    "draft",
    "ready",
    "active",
    "completed",
    "cancelled",
    "archived",
]

SourceKindField = Literal[
    "fair",
    "import",
    "segment",
    "manual_selection",
    "customer",
    "none",
]

PriorityField = Literal["low", "normal", "high", "urgent"]


class CreateOperationRequest(BaseModel):
    operation_type: OperationTypeField
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=10000)
    source_kind: SourceKindField = "none"
    source_ids: list[UUID] = Field(default_factory=list)
    source_config: dict[str, Any] = Field(default_factory=dict)
    type_config: dict[str, Any] = Field(default_factory=dict)
    run_settings: dict[str, Any] = Field(default_factory=dict)
    priority: PriorityField = "normal"
    status: OperationStatusField = "draft"
    start_immediately: bool = False


class OperationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    operation_id: UUID
    status: str
    progress: float
    total_items: int
    processed_items: int
    succeeded_items: int
    failed_items: int
    attempt: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_code: Optional[str]
    error_message: Optional[str]
    error_details: dict[str, Any]
    core_job_id: Optional[UUID]
    triggered_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class RelatedResourceResponse(BaseModel):
    type: str
    id: UUID


class OperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    operation_type: str
    title: str
    description: Optional[str]
    status: str
    source_kind: str
    source_ids: list[UUID] = Field(default_factory=list)
    source_config: dict[str, Any]
    type_config: dict[str, Any]
    run_settings: dict[str, Any]
    priority: str
    latest_run_id: Optional[UUID]
    related_todo_id: Optional[UUID] = None
    related_resource: Optional[RelatedResourceResponse] = None
    created_by: UUID
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    capabilities: dict[str, bool] = Field(default_factory=dict)
    latest_run: Optional[OperationRunResponse] = None


class OperationDetailResponse(BaseModel):
    operation: OperationResponse
    runs: list[OperationRunResponse]


class OperationListResponse(StandardListResponse[OperationResponse]):
    pass


class OperationRunListResponse(StandardListResponse[OperationRunResponse]):
    pass


class WizardStepResponse(BaseModel):
    id: str
    required: bool
    order: int


class OperationTypeMetadataResponse(BaseModel):
    type: str
    label_key: str
    description_key: str
    supported_sources: list[str]
    default_source: str
    capabilities: dict[str, bool]
    wizard_steps: list[WizardStepResponse]
    type_config_schema: dict[str, Any]
    run_settings_schema: dict[str, Any]
    available_in_wizard: bool
    handler_registered: bool


class WizardMetadataResponse(BaseModel):
    types: list[OperationTypeMetadataResponse]
    source_kinds: list[str]
    capabilities_keys: list[str]


class OperationTypeCatalogItemResponse(BaseModel):
    key: str
    name: str
    is_active: bool
    sort_order: int
    supports_pause: bool
    supports_resume: bool
    supports_retry: bool
    supports_schedule: bool
    supports_items: bool
    updated_at: datetime


class OperationTypeCatalogListResponse(BaseModel):
    items: list[OperationTypeCatalogItemResponse]


class UpdateOperationTypeCapabilitiesRequest(BaseModel):
    supports_pause: bool
    supports_resume: bool
    supports_retry: bool
    supports_schedule: bool
    supports_items: bool
    is_active: bool


class ErrorResponse(BaseModel):
    detail: str


class BulkEmailOperationRecipientOptionsRequest(BaseModel):
    include_customer_emails: bool = True
    include_contact_emails: bool = True
    skip_no_email: bool = True
    exclude_inactive: bool = True
    dedupe_emails: bool = True


class BulkEmailOperationPreviewPayload(BaseModel):
    source_type: Literal["manual", "fair_list"]
    template_id: UUID
    smtp_account_id: UUID
    subject_override: str | None = None
    manual_emails: str | None = None
    fair_ids: list[UUID] = Field(default_factory=list)
    country_filter: str | None = None
    city_filter: str | None = None
    company_name_contains: str | None = None
    recipient_options: BulkEmailOperationRecipientOptionsRequest = Field(
        default_factory=BulkEmailOperationRecipientOptionsRequest
    )


class BulkEmailOperationPreviewRecipientResponse(BaseModel):
    recipient_key: str
    email: str
    source: str
    status: str
    skip_reason: str | None = None
    recipient_name: str | None = None
    company_name: str | None = None
    fair_id: UUID | None = None
    fair_name: str | None = None
    customer_id: UUID | None = None
    contact_id: UUID | None = None
    participation_id: UUID | None = None


class BulkEmailOperationRecipientSummaryResponse(BaseModel):
    source_type: Literal["manual", "fair_list"]
    total_found: int | None = None
    valid_email_count: int
    duplicate_count: int | None = None
    invalid_count: int | None = None
    deduped_recipient_count: int
    skipped_count: int
    selected_fair_count: int | None = None
    selected_fair_names: list[str] | None = None
    total_customers: int | None = None
    total_contacts: int | None = None
    recipients: list[BulkEmailOperationPreviewRecipientResponse]


class BulkEmailOperationMailPreviewResponse(BaseModel):
    template_id: UUID
    template_name: str
    smtp_account_id: UUID
    smtp_account_name: str
    rendered_subject: str
    body_html: str | None = None
    body_text: str | None = None


class BulkEmailOperationPreviewResponse(BaseModel):
    recipients: BulkEmailOperationRecipientSummaryResponse
    mail: BulkEmailOperationMailPreviewResponse


class BulkEmailOperationSendPayload(BaseModel):
    source_type: Literal["manual", "fair_list"]
    template_id: UUID
    smtp_account_id: UUID
    subject: str
    title: str | None = None
    manual_emails: str | None = None
    fair_ids: list[UUID] = Field(default_factory=list)
    country_filter: str | None = None
    city_filter: str | None = None
    company_name_contains: str | None = None
    recipient_options: BulkEmailOperationRecipientOptionsRequest = Field(
        default_factory=BulkEmailOperationRecipientOptionsRequest
    )
    client_token: str | None = None


class BulkEmailOperationSendResponse(BaseModel):
    operation_id: UUID
    batch_id: UUID | None = None
    status: str
    total_count: int = 0
    message: str = ""


class BulkEmailOperationRecipientRowResponse(BaseModel):
    id: UUID
    email: str
    company_name: str
    recipient_name: str | None = None
    source: str
    status: str
    error_message: str | None = None
    send_attempt: int = 1
    sent_at: datetime | None = None
    customer_id: UUID | None = None
    contact_id: UUID | None = None
    participation_id: UUID | None = None
    fair_name: str | None = None


class BulkEmailOperationRecipientsResponse(BaseModel):
    batch_id: UUID
    items: list[BulkEmailOperationRecipientRowResponse]


class BulkEmailOperationLogLineResponse(BaseModel):
    at: datetime | None = None
    level: str = "info"
    message: str
    outbox_id: UUID | None = None
    email: str | None = None
    status: str | None = None


class BulkEmailOperationLogsResponse(BaseModel):
    batch_id: UUID
    items: list[BulkEmailOperationLogLineResponse]
