from datetime import UTC, datetime
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.data_integration.application.adapters.registry import get_source_adapter_registry
from app.modules.data_integration.domain.source_adapter import SourceConnection
from app.modules.imports.application.column_mapper import build_mapping_preview_columns, suggest_column_mapping
from app.modules.imports.application.commands import UploadRawImportCommand, UploadRawImportResult
from app.modules.imports.domain.entities import ImportBatch
from app.modules.imports.domain.exceptions import FairRequiredError
from app.modules.imports.domain.import_limits import ImportLimits
from app.modules.imports.domain.ports import ImportBatchRepository
from app.modules.imports.domain.value_objects import ExcelHeaderMode

PERMISSION_CREATE = "fair_crm.imports.create"


class UploadRawImportUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        fair_repository: FairRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._fair_repository = fair_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UploadRawImportCommand) -> UploadRawImportResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        if command.fair_id is None:
            raise FairRequiredError("fair_id is required")

        limits = ImportLimits.from_settings(get_settings())
        limits.validate_file_size(len(command.file_content))

        adapter = get_source_adapter_registry().get_for_file(command.file_name)
        raw_preview = adapter.preview(
            SourceConnection(payload=command.file_content, file_name=command.file_name),
        )

        fair = self._fair_repository.get_by_id(command.organization_id, command.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")

        suggested = suggest_column_mapping(raw_preview)
        now = datetime.now(tz=UTC)

        batch = ImportBatch.create(
            organization_id=command.organization_id,
            fair_id=command.fair_id,
            file_name=command.file_name,
            source_type=adapter.source_type,
            total_rows=raw_preview["total_rows"],
            raw_preview_json=raw_preview,
            stored_file_content=command.file_content,
            now=now,
        )
        saved = self._batch_repository.add(batch)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.uploaded_raw",
            resource_type="import_batch",
            resource_id=str(saved.id),
            new_values={"file_name": saved.file_name, "fair_id": str(saved.fair_id)},
            metadata={"user_id": str(command.user_id)},
        )

        sample_rows = raw_preview["rows"][: limits.mapping_sample_rows]
        mapping_columns = build_mapping_preview_columns(
            raw_preview,
            header_mode=ExcelHeaderMode(suggested["header_mode"]),
            header_row_index=suggested.get("header_row_index"),
            max_sample_rows=limits.mapping_sample_rows,
        )
        return UploadRawImportResult(
            batch_id=saved.id,
            fair_id=saved.fair_id,
            source_type=saved.source_type,
            detected_headers=raw_preview["detected_headers"],
            raw_columns=raw_preview["columns"],
            mapping_columns=mapping_columns,
            sample_rows=sample_rows,
            total_rows=raw_preview["total_rows"],
            suggested_mapping=suggested,
            status=saved.status,
            file_name=saved.file_name,
            available_sheets=raw_preview.get("available_sheets") or [],
            selected_sheet_name=raw_preview.get("sheet_name"),
        )
