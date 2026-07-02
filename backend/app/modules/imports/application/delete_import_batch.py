from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.data_integration.domain.ports import ImportJobRepository
from app.modules.imports.application.commands import DeleteImportBatchCommand, DeleteImportBatchResult
from app.modules.imports.domain.batch_status import has_active_batch_operation
from app.modules.imports.domain.exceptions import ImportBatchDeleteBlockedError, ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository

PERMISSION_DELETE = "fair_crm.imports.delete"


class DeleteImportBatchUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        job_repository: ImportJobRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._job_repository = job_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: DeleteImportBatchCommand) -> DeleteImportBatchResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        batch = self._batch_repository.get_by_id(command.organization_id, command.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")

        if has_active_batch_operation(batch.status):
            raise ImportBatchDeleteBlockedError()
        if self._job_repository.has_any_active_job_for_batch(
            command.organization_id, command.batch_id
        ):
            raise ImportBatchDeleteBlockedError()

        file_name = batch.file_name
        deleted = self._batch_repository.delete(command.organization_id, command.batch_id)
        if not deleted:
            raise ImportBatchNotFoundError("Import batch not found")

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.delete_permanent",
            resource_type="import_batch",
            resource_id=str(command.batch_id),
            old_values={"file_name": file_name},
            metadata={"user_id": str(command.user_id)},
        )

        return DeleteImportBatchResult(batch_id=command.batch_id, deleted=True)
