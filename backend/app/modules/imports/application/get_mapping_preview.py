from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.imports.application.column_mapper import build_mapping_preview_columns
from app.modules.imports.application.commands import GetMappingPreviewQuery
from app.modules.imports.domain.exceptions import ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository
from app.modules.imports.domain.value_objects import ExcelHeaderMode

PERMISSION_READ = "fair_crm.imports.read"


@dataclass
class GetMappingPreviewResult:
    batch_id: UUID
    header_mode: str
    header_row_index: int | None
    columns: list[dict[str, Any]]


class GetMappingPreviewUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._batch_repository = batch_repository
        self._authorization = authorization

    def execute(self, query: GetMappingPreviewQuery) -> GetMappingPreviewResult:
        if not self._authorization.check_permission(
            organization_id=query.organization_id,
            user_id=query.user_id,
            permission_code=PERMISSION_READ,
            access_token=query.access_token,
        ):
            raise ForbiddenError("Permission denied")

        batch = self._batch_repository.get_by_id(query.organization_id, query.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")

        raw_preview = batch.raw_preview_json or {}
        mode = query.header_mode
        if mode is None and batch.header_mode is not None:
            mode = ExcelHeaderMode(batch.header_mode)
        header_row_index = query.header_row_index
        if header_row_index is None and batch.header_row_index is not None:
            header_row_index = batch.header_row_index
        if mode == ExcelHeaderMode.MANUAL_HEADER_ROW and header_row_index is None:
            header_row_index = 0

        has_header_row = None if mode is None else mode != ExcelHeaderMode.NO_HEADER
        columns = build_mapping_preview_columns(
            raw_preview,
            has_header_row=has_header_row,
            header_mode=mode,
            header_row_index=header_row_index,
        )
        resolved_mode = mode or ExcelHeaderMode.FIRST_ROW_HEADER
        resolved_index = header_row_index if resolved_mode != ExcelHeaderMode.NO_HEADER else None

        return GetMappingPreviewResult(
            batch_id=batch.id,
            header_mode=resolved_mode.value,
            header_row_index=resolved_index,
            columns=columns,
        )
