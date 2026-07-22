from dataclasses import asdict

from app.modules.operations.domain.entities import Operation, OperationRun, OperationRunItem
from app.modules.operations.domain.handler import OperationHandler
from app.modules.operations.domain.source_normalization import extract_source_ids
from app.modules.operations.domain.type_registry import (
    OperationTypeDefinition,
    default_operation_type_registry,
)
from app.modules.operations.domain.value_objects import HandlerCapabilities
from app.modules.operations.application.commands import (
    OperationResult,
    OperationRunItemResult,
    OperationRunResult,
    WizardMetadataResult,
)


def capabilities_to_dict(capabilities: HandlerCapabilities) -> dict[str, bool]:
    return asdict(capabilities)


def resolve_capabilities(
    operation_type: str,
    handler: OperationHandler | None,
) -> dict[str, bool]:
    if handler is not None:
        return capabilities_to_dict(handler.capabilities)
    definition = default_operation_type_registry.get(operation_type)
    if definition is None:
        return capabilities_to_dict(HandlerCapabilities())
    return capabilities_to_dict(definition.capabilities)


def operation_to_result(
    operation: Operation,
    *,
    handler: OperationHandler | None = None,
    latest_run: OperationRun | None = None,
) -> OperationResult:
    return OperationResult(
        id=operation.id,
        organization_id=operation.organization_id,
        operation_type=operation.operation_type,
        title=operation.title,
        description=operation.description,
        status=operation.status,
        source_kind=operation.source_kind,
        source_ids=extract_source_ids(operation.source_config),
        source_config=dict(operation.source_config or {}),
        type_config=dict(operation.type_config or {}),
        run_settings=dict(operation.run_settings or {}),
        priority=operation.priority,
        latest_run_id=operation.latest_run_id,
        related_todo_id=operation.related_todo_id,
        related_resource=(
            {"type": "todo", "id": operation.related_todo_id}
            if operation.related_todo_id is not None
            else None
        ),
        created_by=operation.created_by,
        updated_by=operation.updated_by,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
        capabilities=resolve_capabilities(operation.operation_type, handler),
        latest_run=run_to_result(latest_run) if latest_run else None,
    )


def run_to_result(run: OperationRun) -> OperationRunResult:
    return OperationRunResult(
        id=run.id,
        organization_id=run.organization_id,
        operation_id=run.operation_id,
        status=run.status,
        progress=run.progress,
        total_items=run.total_items,
        processed_items=run.processed_items,
        succeeded_items=run.succeeded_items,
        failed_items=run.failed_items,
        attempt=run.attempt,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_code=run.error_code,
        error_message=run.error_message,
        error_details=dict(run.error_details or {}),
        core_job_id=run.core_job_id,
        triggered_by=run.triggered_by,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def run_item_to_result(item: OperationRunItem) -> OperationRunItemResult:
    return OperationRunItemResult(
        id=item.id,
        organization_id=item.organization_id,
        run_id=item.run_id,
        operation_id=item.operation_id,
        item_key=item.item_key,
        target_type=item.target_type,
        target_id=item.target_id,
        status=item.status,
        attempt=item.attempt,
        payload=dict(item.payload or {}),
        result=dict(item.result or {}),
        error_code=item.error_code,
        error_message=item.error_message,
        started_at=item.started_at,
        finished_at=item.finished_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def type_definition_to_dict(
    definition: OperationTypeDefinition,
    *,
    handler: OperationHandler | None,
) -> dict:
    capabilities = (
        capabilities_to_dict(handler.capabilities)
        if handler is not None
        else capabilities_to_dict(definition.capabilities)
    )
    return {
        "type": definition.type,
        "label_key": definition.label_key,
        "description_key": definition.description_key,
        "supported_sources": list(definition.supported_sources),
        "default_source": definition.default_source,
        "capabilities": capabilities,
        "wizard_steps": [
            {
                "id": step.id,
                "required": step.required,
                "order": step.order,
            }
            for step in definition.wizard_steps
        ],
        "type_config_schema": definition.type_config_schema,
        "run_settings_schema": definition.run_settings_schema,
        "available_in_wizard": definition.available_in_wizard,
        "handler_registered": handler is not None,
        "execution_ready": capabilities.get("execution_ready", False),
    }


def build_wizard_metadata(
    *,
    type_registry,
    handler_registry,
) -> WizardMetadataResult:
    types = []
    for definition in type_registry.list_wizard_types():
        handler = handler_registry.get(definition.type)
        types.append(type_definition_to_dict(definition, handler=handler))
    return WizardMetadataResult(
        types=types,
        source_kinds=[
            "fair",
            "import",
            "segment",
            "manual_selection",
            "customer",
            "none",
        ],
        capabilities_keys=[
            "supports_pause",
            "supports_resume",
            "supports_retry",
            "supports_schedule",
            "supports_items",
            "requires_worker",
            "execution_ready",
        ],
    )
