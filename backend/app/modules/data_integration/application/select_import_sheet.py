from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.data_integration.application.adapters.registry import get_source_adapter_registry
from app.modules.data_integration.domain.source_adapter import SourceConnection
from app.modules.imports.application.column_mapper import suggest_column_mapping
from app.modules.imports.application.commands import SelectImportSheetCommand
from app.modules.imports.domain.exceptions import ImportBatchNotFoundError, InvalidImportFileError
from app.modules.imports.domain.ports import ImportBatchRepository
from app.modules.imports.domain.value_objects import ImportBatchStatus

PERMISSION_UPDATE = "fair_crm.imports.update"


@dataclass
class SelectImportSheetResult:
    batch_id: UUID
    selected_sheet_name: str
    total_rows: int
    suggested_mapping: dict
    available_sheets: list[str]


class SelectImportSheetUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: SelectImportSheetCommand) -> SelectImportSheetResult:
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
        if batch.status == ImportBatchStatus.APPLIED:
            raise InvalidImportFileError("Cannot change sheet on applied batch")

        file_content = batch.stored_file_content or command.file_content
        if not file_content:
            raise InvalidImportFileError("Stored file not available; re-upload required")

        adapter = get_source_adapter_registry().get(batch.source_type)
        raw_preview = adapter.preview(
            SourceConnection(payload=file_content, file_name=batch.file_name),
            sheet_name=command.sheet_name,
        )
        suggested = suggest_column_mapping(raw_preview)
        now = datetime.now(tz=UTC)
        batch.set_sheet(sheet_name=command.sheet_name, raw_preview_json=raw_preview, now=now)
        batch.stored_file_content = file_content
        batch.column_mapping_json = None
        batch.has_header_row = None
        batch.header_mode = None
        batch.header_row_index = None
        batch.status = ImportBatchStatus.UPLOADED
        updated = self._batch_repository.update(batch)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.data_integration.sheet_selected",
            resource_type="import_batch",
            resource_id=str(updated.id),
            new_values={"sheet_name": command.sheet_name},
            metadata={"user_id": str(command.user_id)},
        )

        return SelectImportSheetResult(
            batch_id=updated.id,
            selected_sheet_name=command.sheet_name,
            total_rows=raw_preview["total_rows"],
            suggested_mapping=suggested,
            available_sheets=raw_preview.get("available_sheets") or [],
        )
