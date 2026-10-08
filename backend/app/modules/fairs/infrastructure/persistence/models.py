from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base

JsonType = JSON().with_variant(SQLiteJSON(), "sqlite")


class SystemFairSeparationModel(Base):
    """A System Fair the user marked as intentionally distinct inside a shared label."""

    __tablename__ = "crm_system_fair_separations"
    __table_args__ = (
        Index(
            "ix_crm_system_fair_separations_identity",
            "source",
            "identity_name",
            "city_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    identity_name: Mapped[str] = mapped_column(String(500), nullable=False)
    city_key: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    fair_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_fairs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FairModel(Base):
    __tablename__ = "crm_fairs"
    __table_args__ = (
        CheckConstraint(
            "(origin = 'organization' AND organization_id IS NOT NULL) "
            "OR (origin = 'system' AND organization_id IS NULL)",
            name="ck_crm_fairs_origin_organization",
        ),
        Index(
            "uq_crm_fairs_system_external_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("origin = 'system'"),
            sqlite_where=text("origin = 'system'"),
        ),
        Index(
            "ix_crm_fairs_system_identity_name",
            "origin",
            "source",
            "identity_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="organization", server_default="organization")
    source: Mapped[str | None] = mapped_column(String(32))
    external_id: Mapped[str | None] = mapped_column(String(64))
    identity_name: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=""
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    organizer: Mapped[str | None] = mapped_column(String(255))
    venue: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    website: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_from_status: Mapped[str | None] = mapped_column(String(32))
    adapter_key: Mapped[str | None] = mapped_column(String(100), index=True)
    source_url: Mapped[str | None] = mapped_column(Text())
    scraper_config: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
