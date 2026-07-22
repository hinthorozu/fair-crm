from app.modules.operations.domain.exceptions import HandlerNotRegisteredError
from app.modules.operations.domain.handler import OperationHandler


class InMemoryHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, OperationHandler] = {}

    def register(self, handler: OperationHandler) -> None:
        self._handlers[handler.operation_type] = handler

    def get(self, operation_type: str) -> OperationHandler | None:
        return self._handlers.get(operation_type)

    def require(self, operation_type: str) -> OperationHandler:
        handler = self.get(operation_type)
        if handler is None:
            raise HandlerNotRegisteredError(
                f"No handler registered for operation type: {operation_type}"
            )
        return handler

    def list_types(self) -> list[str]:
        return sorted(self._handlers.keys())
