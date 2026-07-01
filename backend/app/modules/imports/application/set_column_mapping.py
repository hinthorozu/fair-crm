from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.imports.application.column_mapper import validate_column_mapping
from app.modules.imports.application.commands import SetColumnMappingCommand, SetColumnMappingResult
from app.modules.imports.domain.exceptions import (
    ImportBatchAlreadyAppliedError,
    ImportBatchNotFoundError,
    InvalidColumnMappingError,
)
from app.modules.imports.domain.ports import ImportBatchRepository
from app.modules.imports.domain.value_objects import ImportBatchStatus

PERMISSION_UPDATE = "fair_crm.imports.update"


class SetColumnMappingUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: SetColumnMappingCommand) -> SetColumnMappingResult:
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
            raise ImportBatchAlreadyAppliedError("Import batch already applied")

        mapping_config: dict[str, Any] = {
            "has_header_row": command.has_header_row,
            "mappings": command.mappings,
        }
        validate_column_mapping(mapping_config)

        now = datetime.now(tz=UTC)
        batch.mark_mapped(mapping=mapping_config, has_header_row=command.has_header_row, now=now)
        updated = self._batch_repository.update(batch)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.mapping_set",
            resource_type="import_batch",
            resource_id=str(updated.id),
            new_values={"mapping_fields": list(command.mappings.keys())},
            metadata={"user_id": str(command.user_id)},
        )

        return SetColumnMappingResult(
            batch_id=updated.id,
            status=updated.status,
            column_mapping=mapping_config,
        )
