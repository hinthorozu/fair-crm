from dataclasses import dataclass

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.operations.application.list_operation_types import OperationTypeListItem
from app.modules.operations.domain.exceptions import InvalidOperationTypeError
from app.modules.operations.domain.value_objects import HandlerCapabilities
from app.modules.operations.infrastructure.repositories.operation_type_repository import (
    SqlAlchemyOperationTypeRepository,
    capabilities_from_model,
)

PERMISSION_CREATE = "fair_crm.operations.create"


@dataclass(frozen=True)
class UpdateOperationTypeCapabilitiesCommand:
    organization_id: object
    user_id: object
    access_token: str
    key: str
    capabilities: HandlerCapabilities
    is_active: bool | None = None


class UpdateOperationTypeCapabilitiesUseCase:
    def __init__(
        self,
        repository: SqlAlchemyOperationTypeRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(self, command: UpdateOperationTypeCapabilitiesCommand) -> OperationTypeListItem:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        row = self._repository.update_capabilities(
            command.key,
            command.capabilities,
            is_active=command.is_active,
        )
        if row is None:
            raise InvalidOperationTypeError(f"Unknown operation type: {command.key}")

        caps = capabilities_from_model(row)
        return OperationTypeListItem(
            key=row.key,
            name=row.name,
            is_active=row.is_active,
            sort_order=row.sort_order,
            supports_pause=caps.supports_pause,
            supports_resume=caps.supports_resume,
            supports_retry=caps.supports_retry,
            supports_schedule=caps.supports_schedule,
            supports_items=caps.supports_items,
            updated_at=row.updated_at,
        )
