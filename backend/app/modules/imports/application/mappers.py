from app.modules.imports.application.batch_display_metadata import resolve_adapter_key_from_batch
from app.modules.imports.application.commands import ImportBatchResult, ImportRowResult
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSourceType


def batch_to_result(
    batch: ImportBatch,
    rows: list[ImportRow] | None = None,
    *,
    source_type: ImportSourceType | None = None,
    fair_name: str | None = None,
) -> ImportBatchResult:
    ready_to_create = 0
    ready_to_update = 0
    if rows:
        ready_to_create = sum(1 for row in rows if row.status == ImportRowStatus.READY_TO_CREATE)
        ready_to_update = sum(1 for row in rows if row.status == ImportRowStatus.READY_TO_UPDATE)

    return ImportBatchResult(
        id=batch.id,
        organization_id=batch.organization_id,
        fair_id=batch.fair_id,
        source_type=source_type or batch.source_type,
        file_name=batch.file_name,
        status=batch.status,
        total_rows=batch.total_rows,
        valid_rows=batch.valid_rows,
        invalid_rows=batch.invalid_rows,
        duplicate_rows=batch.duplicate_rows,
        created_rows=batch.created_rows,
        updated_rows=batch.updated_rows,
        skipped_rows=batch.skipped_rows,
        created_participations=batch.created_participations,
        updated_participations=batch.updated_participations,
        ready_to_create=ready_to_create,
        ready_to_update=ready_to_update,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        completed_at=batch.completed_at,
        notes=batch.notes,
        selected_sheet_name=batch.selected_sheet_name,
        available_sheets=(batch.raw_preview_json or {}).get("available_sheets") or [],
        header_mode=batch.header_mode.value if batch.header_mode else None,
        has_header_row=batch.has_header_row,
        header_row_index=batch.header_row_index,
        column_mapping_json=batch.column_mapping_json,
        fair_name=fair_name,
        adapter_key=resolve_adapter_key_from_batch(batch),
    )


def row_to_result(
    row: ImportRow,
    *,
    match_customer_name: str | None = None,
    merge_preview: dict | None = None,
) -> ImportRowResult:
    return ImportRowResult(
        id=row.id,
        batch_id=row.batch_id,
        row_number=row.row_number,
        raw_data_json=row.raw_data_json,
        normalized_data_json=row.normalized_data_json,
        status=row.status,
        validation_errors_json=row.validation_errors_json,
        match_customer_id=row.match_customer_id,
        match_customer_name=match_customer_name,
        match_confidence=row.match_confidence,
        match_reason=row.match_reason,
        participation_exists=row.participation_exists,
        suggested_action=row.suggested_action.value if row.suggested_action else None,
        decision=row.decision,
        created_customer_id=row.created_customer_id,
        updated_customer_id=row.updated_customer_id,
        created_participation_id=row.created_participation_id,
        updated_participation_id=row.updated_participation_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        merge_preview=merge_preview,
    )
