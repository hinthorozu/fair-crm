from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuoteModel(Base):
    __tablename__ = "crm_quotes"
    __table_args__ = (UniqueConstraint("organization_id", "todo_id", name="uq_quote_org_todo"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    todo_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("crm_todos.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("crm_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    fair_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("crm_fairs.id", ondelete="RESTRICT"), nullable=False, index=True)
    template_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("crm_quote_templates.id", ondelete="RESTRICT"), nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    selected_items: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
