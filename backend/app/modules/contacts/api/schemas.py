from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse


class CreateContactRequest(BaseModel):
    customer_id: UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    title: Optional[str] = Field(default=None, max_length=255)
    department: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Single email or semicolon-separated list (commas accepted on input).",
        examples=["info@abc.com;sales@abc.com"],
    )
    phone: Optional[str] = Field(default=None, max_length=50)
    mobile_phone: Optional[str] = Field(default=None, max_length=50)
    linkedin: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=5000)
    is_primary: bool = False
    is_active: bool = True
    email_allowed: bool = True
    sms_allowed: bool = True
    consent_note: Optional[str] = Field(default=None, max_length=5000)


class UpdateContactRequest(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    title: Optional[str] = Field(default=None, max_length=255)
    department: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Single email or semicolon-separated list (commas accepted on input).",
        examples=["info@abc.com;sales@abc.com"],
    )
    phone: Optional[str] = Field(default=None, max_length=50)
    mobile_phone: Optional[str] = Field(default=None, max_length=50)
    linkedin: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=5000)
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    email_allowed: Optional[bool] = None
    sms_allowed: Optional[bool] = None
    consent_note: Optional[str] = Field(default=None, max_length=5000)


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    customer_id: UUID
    first_name: str
    last_name: str
    full_name: str
    title: Optional[str]
    department: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    mobile_phone: Optional[str]
    linkedin: Optional[str]
    notes: Optional[str]
    is_primary: bool
    is_active: bool
    email_allowed: bool = True
    sms_allowed: bool = True
    email_unsubscribed_at: Optional[datetime] = None
    sms_unsubscribed_at: Optional[datetime] = None
    consent_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


class ContactListResponse(StandardListResponse[ContactResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str
