"""Whether an import job is genuinely in progress (vs orphaned queued rows)."""

from app.modules.data_integration.domain.entities import ImportJob
from app.modules.imports.domain.batch_status import (
    ACTIVE_ANALYZE_BATCH_STATUSES,
    normalize_batch_status,
)
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportJobStatus, ImportJobType


def is_import_job_active_for_batch(batch_status: str, job: ImportJob) -> bool:
    """True only when the job reflects real in-flight work for the batch status."""
    if job.status == ImportJobStatus.RUNNING:
        return True
    if job.status != ImportJobStatus.QUEUED:
        return False

    normalized = normalize_batch_status(batch_status)
    if job.job_type == ImportJobType.ANALYZE:
        return normalized in ACTIVE_ANALYZE_BATCH_STATUSES
    if job.job_type in (ImportJobType.APPLY, ImportJobType.BULK_DECISION):
        return normalized == ImportBatchStatus.APPLYING
    return False
