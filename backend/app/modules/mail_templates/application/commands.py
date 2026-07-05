from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.modules.mail_templates.domain.value_objects import MailTemplateType


@dataclass(frozen=True)
class CreateMailTemplateCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    name: str
    key: str
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    template_type: str | MailTemplateType = MailTemplateType.TRANSACTIONAL
    language: str = "tr"
    is_active: bool = True
    is_default: bool = False
    variables_schema: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class UpdateMailTemplateCommand:
    organization_id: UUID
    template_id: UUID
    access_token: str
    user_id: UUID
    name: Optional[str] = None
    key: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    template_type: str | MailTemplateType | None = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    variables_schema: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class GetMailTemplateQuery:
    organization_id: UUID
    template_id: UUID


@dataclass(frozen=True)
class ListMailTemplatesQuery:
    organization_id: UUID


@dataclass(frozen=True)
class DeleteMailTemplateCommand:
    organization_id: UUID
    template_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class RenderMailTemplateCommand:
    organization_id: UUID
    template_id: UUID
    access_token: str
    user_id: UUID
    variables: dict[str, Any]


@dataclass(frozen=True)
class MailTemplateResult:
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
    deleted_at: Optional[datetime]


@dataclass(frozen=True)
class MailTemplateListResult:
    items: list[MailTemplateResult]


@dataclass(frozen=True)
class RenderMailTemplateResult:
    subject: str
    body_html: Optional[str]
    body_text: Optional[str]


@dataclass(frozen=True)
class SendTestMailTemplateCommand:
    organization_id: UUID
    template_id: UUID
    access_token: str
    user_id: UUID
    to_email: str
    variables: dict[str, Any]
    smtp_account_id: UUID | None = None
    subject_override: str | None = None


@dataclass(frozen=True)
class SendTestMailTemplateResult:
    success: bool
    message: str
    smtp_host: str | None = None
    smtp_port: int | None = None
    template_key: str | None = None
