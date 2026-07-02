from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSystemBackupRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class SystemBackupResponse(BaseModel):
    id: UUID
    file_name: str
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
    download_count: int
    error_message: str | None


class CreateSystemBackupResponse(BaseModel):
    id: UUID
    file_name: str
    status: str
    progress_stage: str


class SystemBackupListResponse(BaseModel):
    items: list[SystemBackupResponse]
    total: int
    page: int
    page_size: int


class RestoreDisabledResponse(BaseModel):
    detail: str
    enabled: bool = False


class ErrorResponse(BaseModel):
    detail: str
