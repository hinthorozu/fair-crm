from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.mail_templates.domain.value_objects import MailTemplateType


class CreateMailTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    key: str = Field(..., min_length=1, max_length=128)
    subject: str = Field(..., min_length=1)
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    template_type: MailTemplateType = MailTemplateType.TRANSACTIONAL
    language: str = Field(default="tr", min_length=2, max_length=16)
    is_active: bool = True
    is_default: bool = False
    variables_schema: Optional[dict[str, Any]] = None


class UpdateMailTemplateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    key: Optional[str] = Field(default=None, min_length=1, max_length=128)
    subject: Optional[str] = Field(default=None, min_length=1)
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    template_type: Optional[MailTemplateType] = None
    language: Optional[str] = Field(default=None, min_length=2, max_length=16)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    variables_schema: Optional[dict[str, Any]] = None


class RenderMailTemplateRequest(BaseModel):
    variables: dict[str, Any] = Field(default_factory=dict)


class RenderMailTemplateResponse(BaseModel):
    subject: str
    body_html: Optional[str]
    body_text: Optional[str]


class SendTestMailTemplateRequest(BaseModel):
    to_email: str = Field(..., min_length=3, max_length=255)
    smtp_account_id: Optional[UUID] = None
    variables: dict[str, Any] = Field(default_factory=dict)
    subject_override: Optional[str] = Field(default=None, min_length=1)


class SendTestMailTemplateResponse(BaseModel):
    success: bool
    message: str
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    template_key: Optional[str] = None


class MailTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    key: str
    subject: str
    body_html: Optional[str]
    body_text: Optional[str]
    template_type: MailTemplateType
    language: str
    is_active: bool
    is_default: bool
    variables_schema: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class MailTemplateListResponse(BaseModel):
    items: list[MailTemplateResponse]


class ErrorResponse(BaseModel):
    detail: str
