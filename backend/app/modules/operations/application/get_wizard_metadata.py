from app.modules.operations.application.commands import WizardMetadataResult
from app.modules.operations.application.mappers import build_wizard_metadata
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.type_registry import OperationTypeRegistry
from app.modules.operations.domain.value_objects import HandlerCapabilities
from app.modules.operations.infrastructure.repositories.operation_type_repository import (
    SqlAlchemyOperationTypeRepository,
    capabilities_from_model,
)


class GetWizardMetadataUseCase:
    def __init__(
        self,
        type_registry: OperationTypeRegistry,
        handler_registry: InMemoryHandlerRegistry,
        operation_type_repository: SqlAlchemyOperationTypeRepository,
    ) -> None:
        self._type_registry = type_registry
        self._handler_registry = handler_registry
        self._operation_type_repository = operation_type_repository

    def execute(self) -> WizardMetadataResult:
        capability_by_key: dict[str, HandlerCapabilities] = {
            row.key: capabilities_from_model(row)
            for row in self._operation_type_repository.list_types(active_only=False)
        }
        return build_wizard_metadata(
            type_registry=self._type_registry,
            handler_registry=self._handler_registry,
            capability_by_key=capability_by_key,
        )
