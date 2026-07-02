from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Boolean

from app.db.base import Base

JsonType = JSON().with_variant(SQLiteJSON(), "sqlite")


class ImportBatchModel(Base):
    __tablename__ = "crm_import_batches"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(index=True)
    fair_id: Mapped[Optional[UUID]] = mapped_column(Uuid, index=True, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="excel")
    file_name: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_rows: Mapped[int] = mapped_column(Integer, default=0)
    updated_rows: Mapped[int] = mapped_column(Integer, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_participations: Mapped[int] = mapped_column(Integer, default=0)
    updated_participations: Mapped[int] = mapped_column(Integer, default=0)
    column_mapping_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    raw_preview_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    has_header_row: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    header_mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    header_row_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    selected_sheet_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stored_file_content: Mapped[Optional[bytes]] = mapped_column(nullable=True)
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
    participation_exists: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    match_participation_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    suggested_action: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_customer_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    updated_customer_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    created_participation_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    updated_participation_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()
