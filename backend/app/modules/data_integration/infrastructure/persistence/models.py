from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base

JsonType = JSON().with_variant(SQLiteJSON(), "sqlite")


class ImportJobModel(Base):
    __tablename__ = "crm_import_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(index=True)
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_import_batches.id", ondelete="CASCADE"), index=True
    )
    job_type: Mapped[str] = mapped_column(String(32), default="apply")
    status: Mapped[str] = mapped_column(String(32))
    progress_processed: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class ImportTemplateModel(Base):
    __tablename__ = "crm_import_templates"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(32), default="excel")
    header_mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    header_row_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mapping_json: Mapped[dict[str, Any]] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()
