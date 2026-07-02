from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerFairParticipationModel(Base):
    __tablename__ = "crm_customer_fair_participations"
    __table_args__ = (
        Index(
            "uq_crm_cfp_active_customer_fair",
            "organization_id",
            "customer_id",
            "fair_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fair_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_fairs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    hall: Mapped[str | None] = mapped_column(String(100))
    stand: Mapped[str | None] = mapped_column(String(100))
    participation_status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="exhibitor")
    notes: Mapped[str | None] = mapped_column(Text)
    primary_contact_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    visited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
