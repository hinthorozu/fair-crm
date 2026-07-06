from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerModel(Base):
    __tablename__ = "crm_customers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(500))
    trade_name: Mapped[str | None] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    customer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tax_number: Mapped[str | None] = mapped_column(String(50))
    tax_office: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    instagram_url: Mapped[str | None] = mapped_column(String(512))
    facebook_url: Mapped[str | None] = mapped_column(String(512))
    linkedin_url: Mapped[str | None] = mapped_column(String(512))
    youtube_url: Mapped[str | None] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    email_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sms_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sms_unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_from_status: Mapped[str | None] = mapped_column(String(32))
