from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

BackupFormatLiteral = Literal["postgresql_dump", "postgresql_sql", "universal_data_package"]
DatabaseKeyLiteral = Literal["kyrox_core", "fair_crm"]


class CreateSystemBackupRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    backup_format: BackupFormatLiteral = "postgresql_dump"
    database_keys: list[DatabaseKeyLiteral] | None = Field(default=None)


class SystemBackupResponse(BaseModel):
    id: UUID
    database_key: str
    database_label: str
    file_name: str
    backup_format: str
    file_size: int | None
    status: str
    progress_stage: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    created_by: UUID
    created_by_email: str | None
    notes: str | None
    checksum: str | None
    manifest_json: dict[str, Any] | None = None
    download_count: int
    error_message: str | None


class CreateSystemBackupResponse(BaseModel):
    id: UUID
    database_key: str
    database_label: str
    file_name: str
    backup_format: str
    status: str
    progress_stage: str


class CreateSystemBackupBatchResponse(BaseModel):
    items: list[CreateSystemBackupResponse]


class SystemBackupListResponse(BaseModel):
    items: list[SystemBackupResponse]
    total: int
    page: int
    page_size: int


class RestoreDisabledResponse(BaseModel):
    detail: str
    enabled: bool = False


class SystemBackupRestoreJobResponse(BaseModel):
    id: UUID
    status: str
    source_type: str
    source_database_key: str
    target_database_key: str
    backup_id: UUID | None = None
    source_file_name: str
    checksum_sha256: str | None = None
    notes: str | None = None
    requested_by_user_id: UUID
    requested_by_email: str | None = None
    requested_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None
    restore_log_path: str | None = None
    message: str
    uploaded: bool = False
    backup_file_name: str | None = None
    backup_format: str | None = None


class RestoreJobLogResponse(BaseModel):
    job_id: UUID
    status: str
    restore_log_path: str | None = None
    exists: bool
    content: str
    truncated: bool = False


class DeleteSystemBackupResponse(BaseModel):
    id: UUID
    file_name: str


class ErrorResponse(BaseModel):
    detail: str
