from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.imports.application.column_mapper import (
    header_mode_to_has_header,
    resolve_header_mode,
    resolve_header_row_index,
)
from app.modules.imports.application.commands import ConfigureImportHeaderCommand
from app.modules.imports.application.commands import ConfigureImportHeaderResult
from app.modules.imports.domain.batch_status import is_batch_terminal
from app.modules.imports.domain.exceptions import ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository

PERMISSION_UPDATE = "fair_crm.imports.update"


class ConfigureImportHeaderUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._batch_repository = batch_repository
        self._authorization = authorization

    def execute(self, command: ConfigureImportHeaderCommand) -> ConfigureImportHeaderResult:
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
            raise ImportBatchNotFoundError("Import batch is closed")

        mode = resolve_header_mode(
            header_mode=command.header_mode,
            has_header_row=command.has_header_row,
        )
        header_row_index = resolve_header_row_index(mode, header_row_index=command.header_row_index)
        has_header = header_mode_to_has_header(mode)

        now = datetime.now(tz=UTC)
        batch.mark_header_configured(
            has_header_row=has_header,
            header_mode=mode,
            header_row_index=header_row_index,
            now=now,
        )
        updated = self._batch_repository.update(batch)

        return ConfigureImportHeaderResult(
            batch_id=updated.id,
            status=updated.status,
            header_mode=mode,
            header_row_index=header_row_index,
            has_header_row=has_header,
        )
