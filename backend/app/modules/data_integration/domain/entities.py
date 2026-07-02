from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.modules.imports.domain.value_objects import ImportJobStatus, ImportJobType


@dataclass
class ImportJob:
    id: UUID
    organization_id: UUID
    batch_id: UUID
    job_type: ImportJobType
    status: ImportJobStatus
    progress_processed: int
    progress_total: int
    result_json: Optional[dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    @classmethod
    def create_apply_job(
        cls,
        *,
        organization_id: UUID,
        batch_id: UUID,
        progress_total: int,
        now: datetime,
    ) -> "ImportJob":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            batch_id=batch_id,
            job_type=ImportJobType.APPLY,
            status=ImportJobStatus.QUEUED,
            progress_processed=0,
            progress_total=progress_total,
            result_json=None,
            error_message=None,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
        )

    def mark_running(self, *, now: datetime) -> None:
        self.status = ImportJobStatus.RUNNING
        self.started_at = now
        self.updated_at = now

    def update_progress(self, *, processed: int, now: datetime) -> None:
        self.progress_processed = processed
        self.updated_at = now

    def mark_completed(self, *, result: dict[str, Any], now: datetime) -> None:
        self.status = ImportJobStatus.COMPLETED
        self.result_json = result
        self.progress_processed = self.progress_total
        self.completed_at = now
        self.updated_at = now

    def mark_failed(self, *, error_message: str, now: datetime) -> None:
        self.status = ImportJobStatus.FAILED
        self.error_message = error_message
        self.completed_at = now
        self.updated_at = now


@dataclass
class ImportTemplate:
    id: UUID
    organization_id: UUID
    name: str
    source_type: str
    header_mode: Optional[str]
    header_row_index: Optional[int]
    mapping_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
