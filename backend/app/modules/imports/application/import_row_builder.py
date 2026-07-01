"""Source-agnostic import row pipeline after extraction.

Pipeline stages:
  Import Source → Extract Rows → Normalize → Validate → Duplicate Detection → Preview → Decision → Apply
"""

from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from app.modules.customers.domain.entities import Customer
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.services.duplicate_detector import (
    BATCH_DUPLICATE_REASON,
    find_customer_match,
)
from app.modules.imports.domain.services.row_normalizer import normalize_row_data
from app.modules.imports.domain.services.row_validator import validate_import_row
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSuggestedAction


def build_import_rows(
    *,
    batch: ImportBatch,
    raw_rows: list[dict[str, Any]],
    customers: list[Customer],
    fair_id: UUID | None,
    participation_exists: Callable[[UUID], tuple[bool, UUID | None]] | None = None,
    now: datetime,
) -> list[ImportRow]:
    seen_names: dict[str, int] = {}
    rows: list[ImportRow] = []

    for index, raw in enumerate(raw_rows, start=1):
        normalized = normalize_row_data(raw)
        errors = validate_import_row(normalized)
        normalized_key = normalized.get("normalized_company_name") or ""

        match_customer_id = None
        match_confidence = None
        match_reason = None
        participation_exists_flag: bool | None = None
        match_participation_id: UUID | None = None
        suggested_action: ImportSuggestedAction | None = None
        status = ImportRowStatus.PENDING

        if errors:
            status = ImportRowStatus.INVALID
            suggested_action = ImportSuggestedAction.SKIP
        else:
            batch_dup = False
            if normalized_key:
                if normalized_key in seen_names:
                    batch_dup = True
                    match_reason = BATCH_DUPLICATE_REASON
                    status = ImportRowStatus.POSSIBLE_DUPLICATE
                    suggested_action = ImportSuggestedAction.SKIP
                else:
                    seen_names[normalized_key] = index

            if not batch_dup:
                match = find_customer_match(normalized_key, customers)
                if match:
                    match_customer_id = match.customer_id
                    match_confidence = match.confidence
                    match_reason = match.reason

                    if fair_id and participation_exists:
                        exists, part_id = participation_exists(match.customer_id)
                        participation_exists_flag = exists
                        match_participation_id = part_id
                        if exists:
                            suggested_action = ImportSuggestedAction.UPDATE_PARTICIPATION
                            status = ImportRowStatus.READY_TO_UPDATE
                        else:
                            suggested_action = ImportSuggestedAction.LINK_EXISTING_CUSTOMER_TO_FAIR
                            status = ImportRowStatus.READY_TO_UPDATE
                    else:
                        status = ImportRowStatus.POSSIBLE_DUPLICATE
                        suggested_action = ImportSuggestedAction.LINK_EXISTING_CUSTOMER_TO_FAIR
                else:
                    status = ImportRowStatus.READY_TO_CREATE
                    suggested_action = ImportSuggestedAction.CREATE_CUSTOMER_AND_PARTICIPATION
                    participation_exists_flag = False

        rows.append(
            ImportRow.create(
                batch_id=batch.id,
                organization_id=batch.organization_id,
                row_number=index,
                raw_data_json=raw,
                normalized_data_json=normalized,
                status=status,
                validation_errors_json=errors or None,
                match_customer_id=match_customer_id,
                match_confidence=match_confidence,
                match_reason=match_reason,
                participation_exists=participation_exists_flag,
                match_participation_id=match_participation_id,
                suggested_action=suggested_action,
                now=now,
            )
        )

    return rows
