from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.data_integration.application.import_job_runner import ApplyJobCommand
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.domain.ports import ImportJobRepository
from app.modules.imports.domain.exceptions import ImportBatchAlreadyAppliedError, ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.value_objects import ImportBatchStatus

PERMISSION_APPLY = "fair_crm.imports.apply"


@dataclass
class StartImportApplyJobCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID


@dataclass
class StartImportApplyJobResult:
    job_id: UUID
    batch_id: UUID
    status: str
    progress_total: int
    apply_command: ApplyJobCommand


class StartImportApplyJobUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        job_repository: ImportJobRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._job_repository = job_repository
        self._authorization = authorization

    def execute(self, command: StartImportApplyJobCommand) -> StartImportApplyJobResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_APPLY,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        batch = self._batch_repository.get_by_id(command.organization_id, command.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")
        if batch.status == ImportBatchStatus.APPLIED:
            raise ImportBatchAlreadyAppliedError("Import batch already applied")

        rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        now = datetime.now(tz=UTC)
        job = ImportJob.create_apply_job(
            organization_id=command.organization_id,
            batch_id=command.batch_id,
            progress_total=len(rows),
            now=now,
        )
        saved = self._job_repository.add(job)

        apply_command = ApplyJobCommand(
            organization_id=command.organization_id,
            user_id=command.user_id,
            access_token=command.access_token,
            batch_id=command.batch_id,
            job_id=saved.id,
        )

        return StartImportApplyJobResult(
            job_id=saved.id,
            batch_id=command.batch_id,
            status=saved.status.value,
            progress_total=saved.progress_total,
            apply_command=apply_command,
        )
