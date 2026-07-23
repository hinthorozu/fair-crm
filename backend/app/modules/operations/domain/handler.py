from dataclasses import dataclass
from typing import Any, Optional, Protocol
from uuid import UUID

from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.value_objects import HandlerCapabilities


@dataclass(frozen=True)
class HandlerValidationResult:
    ok: bool
    errors: tuple[str, ...] = ()

    @classmethod
    def success(cls) -> "HandlerValidationResult":
        return cls(ok=True)

    @classmethod
    def failure(cls, *errors: str) -> "HandlerValidationResult":
        return cls(ok=False, errors=tuple(errors))


@dataclass(frozen=True)
class HandlerExecutionContext:
    """Runtime context passed into handler start/cancel/retry."""

    user_id: UUID
    access_token: str


@dataclass(frozen=True)
class HandlerStartResult:
    """Outcome of starting an operation run via its handler."""

    run_status: str
    total_items: int = 0
    message: Optional[str] = None
    result_payload: dict[str, Any] | None = None
    related_todo_id: UUID | None = None


class OperationHandler(Protocol):
    """Product handler contract. Engine stays agnostic of type-specific rules."""

    operation_type: str

    @property
    def capabilities(self) -> HandlerCapabilities: ...

    def validate_create(
        self,
        *,
        source_kind: str,
        source_config: dict[str, Any],
        type_config: dict[str, Any],
        run_settings: dict[str, Any],
        organization_id: UUID | None = None,
    ) -> HandlerValidationResult: ...

    def validate_start(
        self,
        *,
        operation: Operation,
    ) -> HandlerValidationResult: ...

    def on_start(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult: ...

    def on_cancel(
        self,
        *,
        operation: Operation,
        run: OperationRun | None,
        context: HandlerExecutionContext | None = None,
    ) -> None: ...

    def on_retry(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult: ...


class OperationHandlerRegistry(Protocol):
    def get(self, operation_type: str) -> OperationHandler | None: ...

    def require(self, operation_type: str) -> OperationHandler: ...

    def list_types(self) -> list[str]: ...
