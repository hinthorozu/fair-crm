from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse

from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType


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
    source: CustomerSource = CustomerSource.MANUAL


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
    source: Optional[CustomerSource] = None


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
    source: CustomerSource
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    possible_duplicates: Optional[list[UUID]] = None


class CustomerListResponse(StandardListResponse[CustomerResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str
