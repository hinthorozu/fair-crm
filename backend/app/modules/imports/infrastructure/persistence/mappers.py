from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import (
    ImportBatchStatus,
    ImportDecision,
    ImportRowStatus,
    ImportSourceType,
    ImportSuggestedAction,
    ExcelHeaderMode,
)
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel, ImportRowModel


def batch_model_to_entity(model: ImportBatchModel) -> ImportBatch:
    return ImportBatch(
        id=model.id,
        organization_id=model.organization_id,
        fair_id=model.fair_id,
        source_type=ImportSourceType(model.source_type),
        file_name=model.file_name,
        status=ImportBatchStatus(model.status),
        total_rows=model.total_rows,
        valid_rows=model.valid_rows,
        invalid_rows=model.invalid_rows,
        duplicate_rows=model.duplicate_rows,
        created_rows=model.created_rows,
        updated_rows=model.updated_rows,
        skipped_rows=model.skipped_rows,
        created_participations=model.created_participations,
        updated_participations=model.updated_participations,
        column_mapping_json=model.column_mapping_json,
        raw_preview_json=model.raw_preview_json,
        has_header_row=model.has_header_row,
        header_mode=ExcelHeaderMode(model.header_mode) if model.header_mode else None,
        header_row_index=model.header_row_index,
        selected_sheet_name=model.selected_sheet_name,
        stored_file_content=model.stored_file_content,
        created_at=model.created_at,
        updated_at=model.updated_at,
        completed_at=model.completed_at,
        notes=model.notes,
    )


def batch_entity_to_model(entity: ImportBatch) -> ImportBatchModel:
    return ImportBatchModel(
        id=entity.id,
        organization_id=entity.organization_id,
        fair_id=entity.fair_id,
        source_type=entity.source_type.value,
        file_name=entity.file_name,
        status=entity.status.value,
        total_rows=entity.total_rows,
        valid_rows=entity.valid_rows,
        invalid_rows=entity.invalid_rows,
        duplicate_rows=entity.duplicate_rows,
        created_rows=entity.created_rows,
        updated_rows=entity.updated_rows,
        skipped_rows=entity.skipped_rows,
        created_participations=entity.created_participations,
        updated_participations=entity.updated_participations,
        column_mapping_json=entity.column_mapping_json,
        raw_preview_json=entity.raw_preview_json,
        has_header_row=entity.has_header_row,
        header_mode=entity.header_mode.value if entity.header_mode else None,
        header_row_index=entity.header_row_index,
        selected_sheet_name=entity.selected_sheet_name,
        stored_file_content=entity.stored_file_content,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        completed_at=entity.completed_at,
        notes=entity.notes,
    )


def update_batch_model_from_entity(model: ImportBatchModel, entity: ImportBatch) -> None:
    model.fair_id = entity.fair_id
    model.source_type = entity.source_type.value
    model.file_name = entity.file_name
    model.status = entity.status.value
    model.total_rows = entity.total_rows
    model.valid_rows = entity.valid_rows
    model.invalid_rows = entity.invalid_rows
    model.duplicate_rows = entity.duplicate_rows
    model.created_rows = entity.created_rows
    model.updated_rows = entity.updated_rows
    model.skipped_rows = entity.skipped_rows
    model.created_participations = entity.created_participations
    model.updated_participations = entity.updated_participations
    model.column_mapping_json = entity.column_mapping_json
    model.raw_preview_json = entity.raw_preview_json
    model.has_header_row = entity.has_header_row
    model.header_mode = entity.header_mode.value if entity.header_mode else None
    model.header_row_index = entity.header_row_index
    model.selected_sheet_name = entity.selected_sheet_name
    model.stored_file_content = entity.stored_file_content
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
        participation_exists=model.participation_exists,
        match_participation_id=model.match_participation_id,
        suggested_action=ImportSuggestedAction(model.suggested_action)
        if model.suggested_action
        else None,
        decision=ImportDecision(model.decision) if model.decision else None,
        created_customer_id=model.created_customer_id,
        updated_customer_id=model.updated_customer_id,
        created_participation_id=model.created_participation_id,
        updated_participation_id=model.updated_participation_id,
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
        participation_exists=entity.participation_exists,
        match_participation_id=entity.match_participation_id,
        suggested_action=entity.suggested_action.value if entity.suggested_action else None,
        decision=entity.decision.value if entity.decision else None,
        created_customer_id=entity.created_customer_id,
        updated_customer_id=entity.updated_customer_id,
        created_participation_id=entity.created_participation_id,
        updated_participation_id=entity.updated_participation_id,
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
    model.participation_exists = entity.participation_exists
    model.match_participation_id = entity.match_participation_id
    model.suggested_action = entity.suggested_action.value if entity.suggested_action else None
    model.decision = entity.decision.value if entity.decision else None
    model.created_customer_id = entity.created_customer_id
    model.updated_customer_id = entity.updated_customer_id
    model.created_participation_id = entity.created_participation_id
    model.updated_participation_id = entity.updated_participation_id
    model.updated_at = entity.updated_at
