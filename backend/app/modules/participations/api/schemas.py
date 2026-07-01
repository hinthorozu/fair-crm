from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.participations.domain.value_objects import ParticipationStatus


class CreateParticipationRequest(BaseModel):
    customer_id: UUID
    fair_id: UUID
    hall: Optional[str] = None
    stand: Optional[str] = None
    participation_status: ParticipationStatus = ParticipationStatus.EXHIBITOR
    notes: Optional[str] = None
    primary_contact_id: Optional[UUID] = None
    visited_at: Optional[datetime] = None


class UpdateParticipationRequest(BaseModel):
    hall: Optional[str] = None
    stand: Optional[str] = None
    participation_status: Optional[ParticipationStatus] = None
    notes: Optional[str] = None
    primary_contact_id: Optional[UUID] = None
    visited_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class ParticipationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    customer_id: UUID
    fair_id: UUID
    hall: Optional[str] = None
    stand: Optional[str] = None
    participation_status: ParticipationStatus
    notes: Optional[str] = None
    primary_contact_id: Optional[UUID] = None
    primary_contact_name: Optional[str] = None
    visited_at: Optional[datetime] = None
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
    participation_status: ParticipationStatus
    primary_contact_name: Optional[str] = None
    visited_at: Optional[datetime] = None
    notes: Optional[str] = None


class CustomerParticipationListResponse(BaseModel):
    items: list[CustomerParticipationListItemResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


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
    participation_status: ParticipationStatus
    primary_contact_name: Optional[str] = None
    visited_at: Optional[datetime] = None
    notes: Optional[str] = None


class FairParticipantListResponse(BaseModel):
    items: list[FairParticipantListItemResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class ErrorResponse(BaseModel):
    detail: str
