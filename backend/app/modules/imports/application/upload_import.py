from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.commands import ImportBatchResult, UploadImportCommand
from app.modules.imports.application.import_row_builder import build_import_rows
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.application.source_adapters.excel_source_adapter import ExcelImportSourceAdapter
from app.modules.imports.domain.entities import ImportBatch
from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.value_objects import ImportRowStatus

PERMISSION_CREATE = "fair_crm.imports.create"


class UploadCustomerImportUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        customer_repository: CustomerRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
        source_adapter: ExcelImportSourceAdapter | None = None,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._customer_repository = customer_repository
        self._authorization = authorization
        self._audit = audit
        self._source_adapter = source_adapter or ExcelImportSourceAdapter()

    def execute(self, command: UploadImportCommand) -> ImportBatchResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        if not command.file_name.lower().endswith(".xlsx"):
            raise InvalidImportFileError("Only .xlsx files are supported")

        raw_rows = self._source_adapter.extract_rows(
            command.file_content, file_name=command.file_name
        )
        source_type = self._source_adapter.source_type
        now = datetime.now(tz=UTC)

        batch = ImportBatch.create_legacy(
            organization_id=command.organization_id,
            file_name=command.file_name,
            total_rows=len(raw_rows),
            now=now,
        )
        saved_batch = self._batch_repository.add(batch)

        customers = self._customer_repository.list_all_active(command.organization_id)
        import_rows = build_import_rows(
            batch=saved_batch,
            raw_rows=raw_rows,
            customers=customers,
            fair_id=None,
            now=now,
        )
        self._row_repository.add_many(import_rows)

        valid_count = sum(
            1
            for row in import_rows
            if row.status
            in (
                ImportRowStatus.READY_TO_CREATE,
                ImportRowStatus.READY_TO_UPDATE,
                ImportRowStatus.POSSIBLE_DUPLICATE,
            )
        )
        invalid_count = sum(1 for row in import_rows if row.status == ImportRowStatus.INVALID)
        duplicate_count = sum(
            1 for row in import_rows if row.status == ImportRowStatus.POSSIBLE_DUPLICATE
        )

        saved_batch.mark_previewed(now=now)
        saved_batch.update_counts(
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            duplicate_rows=duplicate_count,
            now=now,
        )
        updated_batch = self._batch_repository.update(saved_batch)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.uploaded",
            resource_type="import_batch",
            resource_id=str(updated_batch.id),
            new_values={"file_name": updated_batch.file_name, "total_rows": updated_batch.total_rows},
            metadata={"user_id": str(command.user_id)},
        )

        return batch_to_result(updated_batch, import_rows, source_type=source_type)
