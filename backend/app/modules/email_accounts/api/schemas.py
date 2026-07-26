from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.smtp.domain.value_objects import SmtpEncryptionType


class ProviderFieldDefinitionResponse(BaseModel):
    key: str
    label: str
    type: str
    required: bool = True
    secret: bool = False
    placeholder: Optional[str] = None
    help_text: Optional[str] = None


class ProviderDefinitionResponse(BaseModel):
    provider_key: str
    display_name: str
    fields: list[ProviderFieldDefinitionResponse]


class ProviderDefinitionListResponse(BaseModel):
    items: list[ProviderDefinitionResponse]


class ErrorPolicyGroupRequest(BaseModel):
    category: str
    identifiers: list[str] = Field(default_factory=list)
    action: str


class ErrorPolicyRequest(BaseModel):
    groups: list[ErrorPolicyGroupRequest] = Field(default_factory=list)


class CreateEmailAccountRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    account_type: str = Field(default="smtp", max_length=32)
    provider_key: Optional[str] = Field(default=None, max_length=64)
    from_email: Optional[str] = Field(default=None, min_length=3, max_length=255)
    from_name: Optional[str] = Field(default=None, max_length=255)
    host: Optional[str] = Field(default=None, min_length=1, max_length=255)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    username: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, max_length=4096)
    encryption_type: SmtpEncryptionType = SmtpEncryptionType.STARTTLS
    is_default: bool = False
    is_active: bool = True
    max_delivery_attempts: int = Field(default=3, ge=1, le=5)
    provider_config: Optional[dict[str, Any]] = None
    error_policy: Optional[ErrorPolicyRequest] = None

    @model_validator(mode="after")
    def validate_by_account_type(self) -> "CreateEmailAccountRequest":
        account_type = (self.account_type or "smtp").strip().lower()
        if account_type == "smtp":
            if not self.host:
                raise ValueError("host is required for smtp accounts")
            if self.port is None:
                raise ValueError("port is required for smtp accounts")
            if not self.from_email:
                raise ValueError("from_email is required for smtp accounts")
        elif account_type == "provider":
            if not self.provider_key:
                raise ValueError("provider_key is required for provider accounts")
            if not self.provider_config:
                raise ValueError("provider_config is required for provider accounts")
        else:
            raise ValueError("account_type must be smtp or provider")
        return self


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
    max_delivery_attempts: Optional[int] = Field(default=None, ge=1, le=5)
    provider_key: Optional[str] = Field(default=None, max_length=64)
    provider_config: Optional[dict[str, Any]] = None
    error_policy: Optional[ErrorPolicyRequest] = None


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
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    encryption_type: Optional[SmtpEncryptionType] = None
    is_default: bool
    is_active: bool
    password_set: bool = False
    max_delivery_attempts: int = 3
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    config_warnings: list[str] = Field(default_factory=list)
    account_type: str = "smtp"
    provider_key: Optional[str] = None
    provider_config: Optional[dict[str, Any]] = None
    secrets_set: dict[str, bool] = Field(default_factory=dict)
    error_policy: Optional[dict[str, Any]] = None


class EmailAccountListResponse(BaseModel):
    items: list[EmailAccountResponse]


class ErrorResponse(BaseModel):
    detail: str
