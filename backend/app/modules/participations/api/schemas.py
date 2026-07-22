from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.schemas.list_response import StandardListResponse


class CreateParticipationRequest(BaseModel):
    customer_id: UUID
    fair_id: UUID
    hall: Optional[str] = None
    stand: Optional[str] = None
    notes: Optional[str] = None


class UpdateParticipationRequest(BaseModel):
    hall: Optional[str] = None
    stand: Optional[str] = None
    notes: Optional[str] = None


class ParticipationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    customer_id: UUID
    fair_id: UUID
    hall: Optional[str] = None
    stand: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class CustomerParticipationListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fair_id: UUID
    fair_name: str
    fair_start_date: Optional[date] = None
    fair_end_date: Optional[date] = None
    hall: Optional[str] = None
    stand: Optional[str] = None
    notes: Optional[str] = None


class CustomerParticipationListResponse(StandardListResponse[CustomerParticipationListItemResponse]):
    pass


class FairParticipantListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    company_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    hall: Optional[str] = None
    stand: Optional[str] = None
    notes: Optional[str] = None


class FairParticipantListResponse(StandardListResponse[FairParticipantListItemResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str
