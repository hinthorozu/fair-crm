from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort, AuditPort
from app.modules.fairs.domain.ports import FairRepository
from app.modules.operations.application.commands import CreateOperationCommand, OperationResult
from app.modules.operations.application.mappers import operation_to_result
from app.modules.operations.application.start_operation import StartOperationUseCase
from app.modules.operations.domain.entities import Operation
from app.modules.operations.domain.exceptions import (
    HandlerNotRegisteredError,
    InvalidOperationConfigError,
    InvalidOperationTypeError,
    InvalidSourceKindError,
)
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.domain.ports import OperationRepository
from app.modules.operations.domain.source_normalization import build_normalized_source_config
from app.modules.operations.domain.type_registry import OperationTypeRegistry
from app.modules.operations.domain.value_objects import OperationStatus, SourceKind

PERMISSION_CREATE = "fair_crm.operations.create"


class CreateOperationUseCase:
    def __init__(
        self,
        operation_repository: OperationRepository,
        type_registry: OperationTypeRegistry,
        handler_registry: InMemoryHandlerRegistry,
        authorization: AuthorizationPort,
        audit: AuditPort,
        fair_repository: FairRepository | None = None,
        start_operation_use_case: StartOperationUseCase | None = None,
    ) -> None:
        self._operation_repository = operation_repository
        self._type_registry = type_registry
        self._handler_registry = handler_registry
        self._authorization = authorization
        self._audit = audit
        self._fair_repository = fair_repository
        self._start_operation_use_case = start_operation_use_case

    def execute(self, command: CreateOperationCommand) -> OperationResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        try:
            definition = self._type_registry.require(command.operation_type)
        except InvalidOperationTypeError:
            raise

        try:
            source_kind, source_config, source_ids = build_normalized_source_config(
                source_kind=command.source_kind,
                source_ids=command.source_ids,
                source_config=command.source_config,
            )
        except (InvalidOperationConfigError, InvalidSourceKindError):
            raise

        if source_kind not in definition.supported_sources:
            raise InvalidOperationConfigError(
                f"source_kind '{source_kind}' is not supported for {command.operation_type}"
            )

        if source_kind == SourceKind.FAIR:
            self._ensure_fairs_exist(command.organization_id, source_ids)

        handler = self._handler_registry.get(command.operation_type)
        if handler is not None:
            validation = handler.validate_create(
                source_kind=source_kind,
                source_config=source_config,
                type_config=command.type_config,
                run_settings=command.run_settings,
                organization_id=command.organization_id,
            )
            if not validation.ok:
                raise InvalidOperationConfigError("; ".join(validation.errors))
        elif command.start_immediately:
            raise HandlerNotRegisteredError(
                f"No executable handler registered for {command.operation_type}"
            )

        type_config = dict(command.type_config)
        if command.operation_type == "manual_task" and "title" in type_config:
            title = str(type_config.get("title") or command.title).strip()
        else:
            title = command.title

        now = datetime.now(tz=UTC)
        initial_status = command.status
        if command.start_immediately and initial_status == OperationStatus.DRAFT:
            initial_status = OperationStatus.READY

        operation = Operation.create(
            organization_id=command.organization_id,
            operation_type=command.operation_type,
            title=title,
            created_by=command.user_id,
            now=now,
            source_kind=source_kind,
            source_config=source_config,
            type_config=type_config,
            run_settings=command.run_settings,
            description=command.description,
            priority=command.priority,
            status=initial_status,
        )
        saved = self._operation_repository.add(operation)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.operation.created",
            resource_type="operation",
            resource_id=str(saved.id),
            new_values={
                "operation_type": saved.operation_type,
                "title": saved.title,
                "status": saved.status,
                "source_kind": saved.source_kind,
                "source_ids": [str(item) for item in source_ids],
            },
            metadata={"user_id": str(command.user_id)},
        )

        result = operation_to_result(saved, handler=handler)

        if command.start_immediately and self._start_operation_use_case is not None:
            from app.modules.operations.application.commands import StartOperationCommand

            started = self._start_operation_use_case.execute(
                StartOperationCommand(
                    organization_id=command.organization_id,
                    user_id=command.user_id,
                    access_token=command.access_token,
                    operation_id=saved.id,
                )
            )
            return started

        return result

    def _ensure_fairs_exist(self, organization_id: UUID, source_ids: list[UUID]) -> None:
        if self._fair_repository is None:
            raise InvalidOperationConfigError("Fair repository is required for fair sources")
        missing: list[str] = []
        for fair_id in source_ids:
            fair = self._fair_repository.get_by_id(organization_id, fair_id)
            if fair is None:
                missing.append(str(fair_id))
        if missing:
            raise InvalidOperationConfigError(
                "One or more source_ids do not reference an existing fair: "
                + ", ".join(missing)
            )
