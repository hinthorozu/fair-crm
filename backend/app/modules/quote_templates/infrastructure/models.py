from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuoteTemplateModel(Base):
    __tablename__ = "crm_quote_templates"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_quote_template_versions.id", ondelete="RESTRICT", use_alter=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    versions: Mapped[list["QuoteTemplateVersionModel"]] = relationship(
        back_populates="template", foreign_keys="QuoteTemplateVersionModel.template_id"
    )


class QuoteTemplateVersionModel(Base):
    __tablename__ = "crm_quote_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version_number", name="uq_quote_template_version"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    template_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("crm_quote_templates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(1024))
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    template: Mapped[QuoteTemplateModel] = relationship(back_populates="versions", foreign_keys=[template_id])
