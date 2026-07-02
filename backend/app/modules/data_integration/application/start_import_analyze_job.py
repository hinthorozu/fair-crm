from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.data_integration.application.import_job_runner import AnalyzeJobCommand
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.domain.ports import ImportJobRepository
from app.modules.imports.domain.batch_status import (
    ACTIVE_ANALYZE_BATCH_STATUSES,
    can_start_analyze,
    is_batch_terminal,
)
from app.modules.imports.domain.exceptions import (
    ImportAnalyzeInProgressError,
    ImportBatchAnalyzeNotAllowedError,
    ImportBatchNotFoundError,
)
from app.modules.imports.domain.ports import ImportBatchRepository

PERMISSION_UPDATE = "fair_crm.imports.update"


@dataclass
class StartImportAnalyzeJobCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID


@dataclass
class StartImportAnalyzeJobResult:
    job_id: UUID
    batch_id: UUID
    status: str
    progress_total: int
    analyze_command: AnalyzeJobCommand


class StartImportAnalyzeJobUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        job_repository: ImportJobRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._batch_repository = batch_repository
        self._job_repository = job_repository
        self._authorization = authorization

    def execute(self, command: StartImportAnalyzeJobCommand) -> StartImportAnalyzeJobResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        batch = self._batch_repository.get_by_id(command.organization_id, command.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")
        if is_batch_terminal(batch.status):
            raise ImportBatchAnalyzeNotAllowedError("Import batch is already completed")
        if not can_start_analyze(batch.status):
            raise ImportBatchAnalyzeNotAllowedError(
                "Analyze can only be started after column mapping is completed"
            )
        if batch.status in ACTIVE_ANALYZE_BATCH_STATUSES:
            raise ImportBatchAnalyzeNotAllowedError("Analyze is already in progress for this batch")

        if self._job_repository.has_active_analyze_job(command.organization_id):
            raise ImportAnalyzeInProgressError()

        existing = self._job_repository.get_active_analyze_job_for_batch(
            command.organization_id, command.batch_id
        )
        if existing is not None:
            raise ImportBatchAnalyzeNotAllowedError("Analyze is already in progress for this batch")

        now = datetime.now(tz=UTC)
        progress_total = batch.total_rows or batch.raw_preview_json.get("total_rows", 0) if batch.raw_preview_json else 0
        job = ImportJob.create_analyze_job(
            organization_id=command.organization_id,
            batch_id=command.batch_id,
            progress_total=max(progress_total, 1),
            now=now,
        )
        saved = self._job_repository.add(job)

        batch.mark_analysis_queued(now=now)
        self._batch_repository.update(batch)

        analyze_command = AnalyzeJobCommand(
            organization_id=command.organization_id,
            user_id=command.user_id,
            access_token=command.access_token,
            batch_id=command.batch_id,
            job_id=saved.id,
        )

        return StartImportAnalyzeJobResult(
            job_id=saved.id,
            batch_id=command.batch_id,
            status=saved.status.value,
            progress_total=saved.progress_total,
            analyze_command=analyze_command,
        )
