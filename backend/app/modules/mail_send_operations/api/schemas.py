from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MailOperationLogEntryResponse(BaseModel):
    time: str
    event: str
    message: str


class MailSendOperationListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    source_type: str
    source_type_label: str
    fair_id: UUID | None
    fair_name: str | None
    customer_id: UUID | None
    customer_name: str | None
    recipient_email: str
    recipient_name: str | None
    smtp_account_id: UUID | None
    smtp_account_name: str | None
    template_id: UUID | None
    template_name: str | None
    subject: str
    status: str
    status_label: str
    error_code: str | None
    error_message: str | None
    operation_logs: list[MailOperationLogEntryResponse] = Field(default_factory=list)
    retry_count: int
    priority: int
    sent_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None


class MailSendOperationListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[MailSendOperationListItemResponse]
    pagination: dict
    sorting: dict
    filters: dict = Field(default_factory=dict)


class RetryMailSendOperationResponse(BaseModel):
    success: bool
    operation: MailSendOperationListItemResponse


class ErrorResponse(BaseModel):
    detail: str
