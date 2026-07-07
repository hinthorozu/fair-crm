from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base

JsonType = JSON().with_variant(SQLiteJSON(), "sqlite")


class SystemDataOperationRunModel(Base):
    __tablename__ = "system_data_operation_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    operation_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    started_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stdout_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_files_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JsonType, nullable=True)
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SystemDataOperationDatasetRowModel(Base):
    __tablename__ = "system_data_operation_dataset_rows"
    __table_args__ = (
        Index(
            "ix_system_data_operation_dataset_rows_run_entity_group",
            "run_id",
            "entity_id",
            "group_by",
            "duplicate_group_key",
            unique=True,
        ),
        Index(
            "ix_system_data_operation_dataset_rows_run_group",
            "run_id",
            "duplicate_group_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    entity_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="customer")
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    duplicate_group_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    group_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicate_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fair_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_fair_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SystemBackupModel(Base):
    __tablename__ = "system_backups"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    backup_format: Mapped[str] = mapped_column(String(32), nullable=False, default="postgresql_dump", index=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    progress_stage: Mapped[str] = mapped_column(String(32), nullable=False, default="preparing")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest_json: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SystemBackupRestoreJobModel(Base):
    __tablename__ = "system_backup_restore_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    backup_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    uploaded_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    requested_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    restore_log_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DuplicateGroupMergeAuditLogModel(Base):
    __tablename__ = "system_duplicate_group_merge_audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    executed_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    executed_by_user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    group_key: Mapped[str] = mapped_column(String(512), nullable=False)
    group_by: Mapped[str] = mapped_column(String(32), nullable=False)
    surviving_customer_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    archived_customer_ids: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    scalar_field_sources: Mapped[dict[str, str]] = mapped_column(JsonType, nullable=False)
    selected_email_ids: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    selected_phone_ids: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    selected_website_ids: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    statistics: Mapped[dict[str, int]] = mapped_column(JsonType, nullable=False)
    reconstruction_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
