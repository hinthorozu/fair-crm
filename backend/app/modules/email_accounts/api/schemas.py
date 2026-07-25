from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.smtp.domain.value_objects import SmtpEncryptionType


class CreateEmailAccountRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    from_email: str = Field(..., min_length=3, max_length=255)
    from_name: Optional[str] = Field(default=None, max_length=255)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    username: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, max_length=4096)
    encryption_type: SmtpEncryptionType = SmtpEncryptionType.STARTTLS
    is_default: bool = False
    is_active: bool = True
    max_delivery_attempts: int = Field(default=3, ge=1, le=5)
    account_type: str = Field(default="smtp", max_length=32)
    provider_key: Optional[str] = Field(default=None, max_length=64)


class UpdateEmailAccountRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    from_email: Optional[str] = Field(default=None, min_length=3, max_length=255)
    from_name: Optional[str] = Field(default=None, max_length=255)
    host: Optional[str] = Field(default=None, min_length=1, max_length=255)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    username: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, max_length=4096)
    encryption_type: Optional[SmtpEncryptionType] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    account_type: Optional[str] = Field(default=None, max_length=32)
    provider_key: Optional[str] = Field(default=None, max_length=64)


class SendTestEmailAccountMailRequest(BaseModel):
    recipient: str = Field(..., min_length=3, max_length=255)


class SendTestEmailAccountMailResponse(BaseModel):
    success: bool
    message: str
    debug_error_type: Optional[str] = None
    debug_error_message: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    encryption_type: Optional[SmtpEncryptionType] = None
    config_warnings: list[str] = Field(default_factory=list)


class EmailAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    from_email: str
    from_name: Optional[str]
    host: str
    port: int
    username: Optional[str]
    encryption_type: SmtpEncryptionType
    is_default: bool
    is_active: bool
    password_set: bool
    max_delivery_attempts: int = 3
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    config_warnings: list[str] = Field(default_factory=list)
    account_type: str = "smtp"
    provider_key: Optional[str] = None


class EmailAccountListResponse(BaseModel):
    items: list[EmailAccountResponse]


class ErrorResponse(BaseModel):
    detail: str
