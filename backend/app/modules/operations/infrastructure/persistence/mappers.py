from app.modules.operations.domain.entities import Operation, OperationRun, OperationRunItem
from app.modules.operations.infrastructure.persistence.models import (
    OperationModel,
    OperationRunItemModel,
    OperationRunModel,
)


def operation_to_model(entity: Operation) -> OperationModel:
    return OperationModel(
        id=entity.id,
        organization_id=entity.organization_id,
        operation_type=entity.operation_type,
        title=entity.title,
        description=entity.description,
        status=entity.status,
        source_kind=entity.source_kind,
        source_config=dict(entity.source_config or {}),
        type_config=dict(entity.type_config or {}),
        run_settings=dict(entity.run_settings or {}),
        priority=entity.priority,
        latest_run_id=entity.latest_run_id,
        related_todo_id=entity.related_todo_id,
        created_by=entity.created_by,
        updated_by=entity.updated_by,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def operation_to_entity(model: OperationModel) -> Operation:
    return Operation(
        id=model.id,
        organization_id=model.organization_id,
        operation_type=model.operation_type,
        title=model.title,
        description=model.description,
        status=model.status,
        source_kind=model.source_kind,
        source_config=dict(model.source_config or {}),
        type_config=dict(model.type_config or {}),
        run_settings=dict(model.run_settings or {}),
        priority=model.priority,
        latest_run_id=model.latest_run_id,
        related_todo_id=model.related_todo_id,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def update_operation_model(model: OperationModel, entity: Operation) -> None:
    model.operation_type = entity.operation_type
    model.title = entity.title
    model.description = entity.description
    model.status = entity.status
    model.source_kind = entity.source_kind
    model.source_config = dict(entity.source_config or {})
    model.type_config = dict(entity.type_config or {})
    model.run_settings = dict(entity.run_settings or {})
    model.priority = entity.priority
    model.latest_run_id = entity.latest_run_id
    model.related_todo_id = entity.related_todo_id
    model.updated_by = entity.updated_by
    model.updated_at = entity.updated_at


def run_to_model(entity: OperationRun) -> OperationRunModel:
    return OperationRunModel(
        id=entity.id,
        organization_id=entity.organization_id,
        operation_id=entity.operation_id,
        status=entity.status,
        progress=entity.progress,
        total_items=entity.total_items,
        processed_items=entity.processed_items,
        succeeded_items=entity.succeeded_items,
        failed_items=entity.failed_items,
        attempt=entity.attempt,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
        error_code=entity.error_code,
        error_message=entity.error_message,
        error_details=dict(entity.error_details or {}),
        core_job_id=entity.core_job_id,
        triggered_by=entity.triggered_by,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def run_to_entity(model: OperationRunModel) -> OperationRun:
    return OperationRun(
        id=model.id,
        organization_id=model.organization_id,
        operation_id=model.operation_id,
        status=model.status,
        progress=model.progress,
        total_items=model.total_items,
        processed_items=model.processed_items,
        succeeded_items=model.succeeded_items,
        failed_items=model.failed_items,
        attempt=model.attempt,
        started_at=model.started_at,
        finished_at=model.finished_at,
        error_code=model.error_code,
        error_message=model.error_message,
        error_details=dict(model.error_details or {}),
        core_job_id=model.core_job_id,
        triggered_by=model.triggered_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def update_run_model(model: OperationRunModel, entity: OperationRun) -> None:
    model.status = entity.status
    model.progress = entity.progress
    model.total_items = entity.total_items
    model.processed_items = entity.processed_items
    model.succeeded_items = entity.succeeded_items
    model.failed_items = entity.failed_items
    model.attempt = entity.attempt
    model.started_at = entity.started_at
    model.finished_at = entity.finished_at
    model.error_code = entity.error_code
    model.error_message = entity.error_message
    model.error_details = dict(entity.error_details or {})
    model.core_job_id = entity.core_job_id
    model.triggered_by = entity.triggered_by
    model.updated_at = entity.updated_at


def run_item_to_model(entity: OperationRunItem) -> OperationRunItemModel:
    return OperationRunItemModel(
        id=entity.id,
        organization_id=entity.organization_id,
        run_id=entity.run_id,
        operation_id=entity.operation_id,
        item_key=entity.item_key,
        target_type=entity.target_type,
        target_id=entity.target_id,
        status=entity.status,
        attempt=entity.attempt,
        payload=dict(entity.payload or {}),
        result=dict(entity.result or {}),
        error_code=entity.error_code,
        error_message=entity.error_message,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def run_item_to_entity(model: OperationRunItemModel) -> OperationRunItem:
    return OperationRunItem(
        id=model.id,
        organization_id=model.organization_id,
        run_id=model.run_id,
        operation_id=model.operation_id,
        item_key=model.item_key,
        target_type=model.target_type,
        target_id=model.target_id,
        status=model.status,
        attempt=model.attempt,
        payload=dict(model.payload or {}),
        result=dict(model.result or {}),
        error_code=model.error_code,
        error_message=model.error_message,
        started_at=model.started_at,
        finished_at=model.finished_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def update_run_item_model(model: OperationRunItemModel, entity: OperationRunItem) -> None:
    model.item_key = entity.item_key
    model.target_type = entity.target_type
    model.target_id = entity.target_id
    model.status = entity.status
    model.attempt = entity.attempt
    model.payload = dict(entity.payload or {})
    model.result = dict(entity.result or {})
    model.error_code = entity.error_code
    model.error_message = entity.error_message
    model.started_at = entity.started_at
    model.finished_at = entity.finished_at
    model.updated_at = entity.updated_at
