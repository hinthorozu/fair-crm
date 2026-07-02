from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.domain.ports import ImportJobRepository


@dataclass
class GetImportJobQuery:
    organization_id: UUID
    job_id: UUID


@dataclass
class ImportJobResult:
    id: UUID
    batch_id: UUID
    job_type: str
    status: str
    progress_processed: int
    progress_total: int
    result_json: Optional[dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    @classmethod
    def from_entity(cls, job: ImportJob) -> "ImportJobResult":
        return cls(
            id=job.id,
            batch_id=job.batch_id,
            job_type=job.job_type.value,
            status=job.status.value,
            progress_processed=job.progress_processed,
            progress_total=job.progress_total,
            result_json=job.result_json,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )


class GetImportJobUseCase:
    def __init__(self, job_repository: ImportJobRepository) -> None:
        self._job_repository = job_repository

    def execute(self, query: GetImportJobQuery) -> ImportJobResult:
        job = self._job_repository.get_by_id(query.organization_id, query.job_id)
        if job is None:
            raise LookupError("Import job not found")
        return ImportJobResult.from_entity(job)
