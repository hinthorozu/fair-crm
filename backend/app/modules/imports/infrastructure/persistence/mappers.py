from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportDecision, ImportRowStatus
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel, ImportRowModel


def batch_model_to_entity(model: ImportBatchModel) -> ImportBatch:
    return ImportBatch(
        id=model.id,
        organization_id=model.organization_id,
        file_name=model.file_name,
        status=ImportBatchStatus(model.status),
        total_rows=model.total_rows,
        valid_rows=model.valid_rows,
        invalid_rows=model.invalid_rows,
        duplicate_rows=model.duplicate_rows,
        created_rows=model.created_rows,
        updated_rows=model.updated_rows,
        skipped_rows=model.skipped_rows,
        created_at=model.created_at,
        updated_at=model.updated_at,
        completed_at=model.completed_at,
        notes=model.notes,
    )


def batch_entity_to_model(entity: ImportBatch) -> ImportBatchModel:
    return ImportBatchModel(
        id=entity.id,
        organization_id=entity.organization_id,
        file_name=entity.file_name,
        status=entity.status.value,
        total_rows=entity.total_rows,
        valid_rows=entity.valid_rows,
        invalid_rows=entity.invalid_rows,
        duplicate_rows=entity.duplicate_rows,
        created_rows=entity.created_rows,
        updated_rows=entity.updated_rows,
        skipped_rows=entity.skipped_rows,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        completed_at=entity.completed_at,
        notes=entity.notes,
    )


def update_batch_model_from_entity(model: ImportBatchModel, entity: ImportBatch) -> None:
    model.file_name = entity.file_name
    model.status = entity.status.value
    model.total_rows = entity.total_rows
    model.valid_rows = entity.valid_rows
    model.invalid_rows = entity.invalid_rows
    model.duplicate_rows = entity.duplicate_rows
    model.created_rows = entity.created_rows
    model.updated_rows = entity.updated_rows
    model.skipped_rows = entity.skipped_rows
    model.updated_at = entity.updated_at
    model.completed_at = entity.completed_at
    model.notes = entity.notes


def row_model_to_entity(model: ImportRowModel) -> ImportRow:
    return ImportRow(
        id=model.id,
        batch_id=model.batch_id,
        organization_id=model.organization_id,
        row_number=model.row_number,
        raw_data_json=model.raw_data_json,
        normalized_data_json=model.normalized_data_json,
        status=ImportRowStatus(model.status),
        validation_errors_json=model.validation_errors_json,
        match_customer_id=model.match_customer_id,
        match_confidence=model.match_confidence,
        match_reason=model.match_reason,
        decision=ImportDecision(model.decision) if model.decision else None,
        created_customer_id=model.created_customer_id,
        updated_customer_id=model.updated_customer_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def row_entity_to_model(entity: ImportRow) -> ImportRowModel:
    return ImportRowModel(
        id=entity.id,
        batch_id=entity.batch_id,
        organization_id=entity.organization_id,
        row_number=entity.row_number,
        raw_data_json=entity.raw_data_json,
        normalized_data_json=entity.normalized_data_json,
        status=entity.status.value,
        validation_errors_json=entity.validation_errors_json,
        match_customer_id=entity.match_customer_id,
        match_confidence=entity.match_confidence,
        match_reason=entity.match_reason,
        decision=entity.decision.value if entity.decision else None,
        created_customer_id=entity.created_customer_id,
        updated_customer_id=entity.updated_customer_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def update_row_model_from_entity(model: ImportRowModel, entity: ImportRow) -> None:
    model.raw_data_json = entity.raw_data_json
    model.normalized_data_json = entity.normalized_data_json
    model.status = entity.status.value
    model.validation_errors_json = entity.validation_errors_json
    model.match_customer_id = entity.match_customer_id
    model.match_confidence = entity.match_confidence
    model.match_reason = entity.match_reason
    model.decision = entity.decision.value if entity.decision else None
    model.created_customer_id = entity.created_customer_id
    model.updated_customer_id = entity.updated_customer_id
    model.updated_at = entity.updated_at
