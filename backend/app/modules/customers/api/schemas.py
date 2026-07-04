from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse

from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType


class CustomerPhoneInputSchema(BaseModel):
    phone: str = Field(..., min_length=1, max_length=50)
    is_primary: bool = False


class CustomerEmailInputSchema(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    is_primary: bool = False


class CustomerWebsiteInputSchema(BaseModel):
    website: str = Field(..., min_length=1, max_length=255)
    is_primary: bool = False


class CreateCustomerRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=500)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    customer_type: CustomerType = CustomerType.LEAD
    status: CustomerStatus = CustomerStatus.LEAD
    website: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Single email or semicolon-separated list (commas accepted on input).",
        examples=["info@abc.com;sales@abc.com"],
    )
    tax_number: Optional[str] = Field(default=None, max_length=50)
    tax_office: Optional[str] = Field(default=None, max_length=255)
    country: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    district: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=2000)
    description: Optional[str] = Field(default=None, max_length=5000)
    instagram_url: Optional[str] = Field(default=None, max_length=512)
    facebook_url: Optional[str] = Field(default=None, max_length=512)
    linkedin_url: Optional[str] = Field(default=None, max_length=512)
    youtube_url: Optional[str] = Field(default=None, max_length=512)
    source: CustomerSource = CustomerSource.MANUAL
    phones: Optional[list[CustomerPhoneInputSchema]] = None
    emails: Optional[list[CustomerEmailInputSchema]] = None
    websites: Optional[list[CustomerWebsiteInputSchema]] = None


class UpdateCustomerRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=500)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    customer_type: Optional[CustomerType] = None
    status: Optional[CustomerStatus] = None
    website: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Single email or semicolon-separated list (commas accepted on input).",
        examples=["info@abc.com;sales@abc.com"],
    )
    tax_number: Optional[str] = Field(default=None, max_length=50)
    tax_office: Optional[str] = Field(default=None, max_length=255)
    country: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    district: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=2000)
    description: Optional[str] = Field(default=None, max_length=5000)
    instagram_url: Optional[str] = Field(default=None, max_length=512)
    facebook_url: Optional[str] = Field(default=None, max_length=512)
    linkedin_url: Optional[str] = Field(default=None, max_length=512)
    youtube_url: Optional[str] = Field(default=None, max_length=512)
    source: Optional[CustomerSource] = None
    phones: Optional[list[CustomerPhoneInputSchema]] = None
    emails: Optional[list[CustomerEmailInputSchema]] = None
    websites: Optional[list[CustomerWebsiteInputSchema]] = None


class CustomerPhoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone: str
    is_primary: bool
    created_at: datetime


class CustomerEmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    is_primary: bool
    created_at: datetime


class CustomerWebsiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    website: str
    is_primary: bool
    created_at: datetime


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    display_name: str
    legal_name: Optional[str]
    trade_name: Optional[str]
    normalized_name: str
    customer_type: CustomerType
    status: CustomerStatus
    website: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    tax_number: Optional[str]
    tax_office: Optional[str]
    country: Optional[str]
    city: Optional[str]
    district: Optional[str]
    address: Optional[str]
    description: Optional[str]
    instagram_url: Optional[str]
    facebook_url: Optional[str]
    linkedin_url: Optional[str]
    youtube_url: Optional[str]
    source: CustomerSource
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    possible_duplicates: Optional[list[UUID]] = None
    phones: list[CustomerPhoneResponse] = Field(default_factory=list)
    emails: list[CustomerEmailResponse] = Field(default_factory=list)
    websites: list[CustomerWebsiteResponse] = Field(default_factory=list)
    phone_extra_count: int = 0
    email_extra_count: int = 0
    website_extra_count: int = 0


class CustomerListResponse(StandardListResponse[CustomerResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str
