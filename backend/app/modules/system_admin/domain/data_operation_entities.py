from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.modules.system_admin.domain.data_operation_value_objects import (
    DataOperationRunResult,
    DataOperationRunStatus,
)


@dataclass(frozen=True)
class DataOperationOutputFile:
    id: UUID
    relative_path: str
    file_name: str
    size_bytes: int | None


@dataclass
class DataOperationRun:
    id: UUID
    organization_id: UUID
    operation_key: str
    status: DataOperationRunStatus
    started_by: UUID
    started_by_email: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    result: DataOperationRunResult | None
    error_message: str | None
    stdout_text: str | None
    output_files: list[DataOperationOutputFile]
    summary_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        operation_key: str,
        started_by: UUID,
        started_by_email: str | None,
        now: datetime,
    ) -> "DataOperationRun":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            operation_key=operation_key,
            status=DataOperationRunStatus.QUEUED,
            started_by=started_by,
            started_by_email=started_by_email,
            started_at=now,
            completed_at=None,
            duration_seconds=None,
            result=None,
            error_message=None,
            stdout_text=None,
            output_files=[],
            summary_json=None,
            created_at=now,
            updated_at=now,
        )

    def mark_running(self, *, now: datetime) -> None:
        self.status = DataOperationRunStatus.RUNNING
        self.updated_at = now

    def mark_completed(
        self,
        *,
        result: DataOperationRunResult,
        output_files: list[DataOperationOutputFile],
        stdout_text: str | None,
        summary_json: dict[str, Any] | None,
        now: datetime,
    ) -> None:
        self.status = DataOperationRunStatus.COMPLETED
        self.result = result
        self.output_files = output_files
        self.stdout_text = stdout_text
        self.summary_json = summary_json
        self.completed_at = now
        self.updated_at = now
        self.error_message = None
        self.duration_seconds = max(0, int((now - self.started_at).total_seconds()))

    def mark_failed(self, *, error_message: str, stdout_text: str | None, now: datetime) -> None:
        self.status = DataOperationRunStatus.FAILED
        self.result = DataOperationRunResult.FAILED
        self.error_message = error_message
        self.stdout_text = stdout_text
        self.completed_at = now
        self.updated_at = now
        self.duration_seconds = max(0, int((now - self.started_at).total_seconds()))
