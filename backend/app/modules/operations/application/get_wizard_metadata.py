from app.modules.operations.application.commands import WizardMetadataResult
from app.modules.operations.application.mappers import build_wizard_metadata
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.type_registry import OperationTypeRegistry


class GetWizardMetadataUseCase:
    def __init__(
        self,
        type_registry: OperationTypeRegistry,
        handler_registry: InMemoryHandlerRegistry,
    ) -> None:
        self._type_registry = type_registry
        self._handler_registry = handler_registry

    def execute(self) -> WizardMetadataResult:
        return build_wizard_metadata(
            type_registry=self._type_registry,
            handler_registry=self._handler_registry,
        )
