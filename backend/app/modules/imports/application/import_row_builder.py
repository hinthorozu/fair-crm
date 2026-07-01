"""Source-agnostic import row pipeline after extraction.

Pipeline stages:
  Import Source → Extract Rows → Normalize → Validate → Duplicate Detection → Preview → Decision → Apply

This module covers Normalize + Validate + Duplicate Detection for preview rows.
Apply is handled by apply_import use case; Extract is handled by source adapters.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.customers.domain.entities import Customer
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.services.duplicate_detector import (
    BATCH_DUPLICATE_REASON,
    find_customer_match,
)
from app.modules.imports.domain.services.row_normalizer import normalize_row_data
from app.modules.imports.domain.services.row_validator import validate_import_row
from app.modules.imports.domain.value_objects import ImportRowStatus


def build_import_rows(
    *,
    batch: ImportBatch,
    raw_rows: list[dict[str, Any]],
    customers: list[Customer],
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
        status = ImportRowStatus.PENDING

        if errors:
            status = ImportRowStatus.INVALID
        else:
            batch_dup = False
            if normalized_key:
                if normalized_key in seen_names:
                    batch_dup = True
                    match_reason = BATCH_DUPLICATE_REASON
                    status = ImportRowStatus.POSSIBLE_DUPLICATE
                else:
                    seen_names[normalized_key] = index

            if not batch_dup:
                match = find_customer_match(normalized_key, customers)
                if match:
                    match_customer_id = match.customer_id
                    match_confidence = match.confidence
                    match_reason = match.reason
                    status = ImportRowStatus.POSSIBLE_DUPLICATE
                else:
                    status = ImportRowStatus.READY_TO_CREATE

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
                now=now,
            )
        )

    return rows
