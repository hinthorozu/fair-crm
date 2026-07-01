from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base

JsonType = JSON().with_variant(SQLiteJSON(), "sqlite")


class ImportBatchModel(Base):
    __tablename__ = "crm_import_batches"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(index=True)
    file_name: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_rows: Mapped[int] = mapped_column(Integer, default=0)
    updated_rows: Mapped[int] = mapped_column(Integer, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ImportRowModel(Base):
    __tablename__ = "crm_import_rows"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_import_batches.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[UUID] = mapped_column(index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    raw_data_json: Mapped[dict[str, Any]] = mapped_column(JsonType)
    normalized_data_json: Mapped[dict[str, Any]] = mapped_column(JsonType)
    status: Mapped[str] = mapped_column(String(32))
    validation_errors_json: Mapped[Optional[list[str]]] = mapped_column(JsonType, nullable=True)
    match_customer_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    match_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    match_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_customer_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    updated_customer_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()
