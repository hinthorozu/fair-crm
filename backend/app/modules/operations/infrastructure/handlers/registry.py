from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.ports import FairRepository
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.infrastructure.handlers.manual_task_handler import (
    ManualTaskHandler,
)
from app.modules.todos.domain.ports import TodoRepository


def build_handler_registry(
    *,
    todo_repository: TodoRepository | None = None,
    fair_repository: FairRepository | None = None,
    customer_repository: CustomerRepository | None = None,
) -> InMemoryHandlerRegistry:
    registry = InMemoryHandlerRegistry()
    registry.register(
        ManualTaskHandler(
            todo_repository=todo_repository,
            fair_repository=fair_repository,
            customer_repository=customer_repository,
        )
    )
    return registry


def build_default_handler_registry() -> InMemoryHandlerRegistry:
    """Registry without Todo wiring — enough for metadata/read paths."""
    return build_handler_registry()


default_handler_registry = build_default_handler_registry()
