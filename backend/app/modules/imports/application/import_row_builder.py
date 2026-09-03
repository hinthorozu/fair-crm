"""Source-agnostic import row pipeline after extraction.

Pipeline stages (isolated responsibilities):
  1. Normalize mapped Excel rows
  2. Validate (Excel + mapping only — no CRM access)
  3. Customer name match (CRM customer index — company name only)
  4. Participation check (minimal fair_id + customer_id lookup)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from app.modules.customers.domain.entities import Customer
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.services.company_name_normalizer import normalize_import_company_name
from app.modules.imports.domain.services.duplicate_detector import (
    BATCH_DUPLICATE_REASON,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_FUZZY,
    MATCH_TYPE_NO_MATCH,
    MATCH_TYPE_WEAK,
    CustomerMatchIndex,
    find_customer_match,
)
from app.modules.imports.domain.services.row_normalizer import normalize_row_data
from app.modules.imports.domain.services.row_validator import validate_import_row
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSuggestedAction


@dataclass
class ValidatedRow:
    row_number: int
    raw: dict[str, Any]
    normalized: dict[str, Any]
    errors: list[str]
    status: ImportRowStatus


def validate_mapped_rows(
    raw_rows: list[dict[str, Any]],
    *,
    seen_names: dict[str, int] | None = None,
    start_row_number: int = 1,
) -> list[ValidatedRow]:
    """Step 5 — Validate Excel rows after column mapping. No CRM data access."""
    validated: list[ValidatedRow] = []
    if seen_names is None:
        seen_names = {}

    for offset, raw in enumerate(raw_rows):
        row_number = start_row_number + offset
        normalized = normalize_row_data(raw)
        errors = validate_import_row(normalized)
        status = ImportRowStatus.INVALID if errors else ImportRowStatus.VALID

        if not errors:
            normalized_key = normalized.get("normalized_company_name") or ""
            if normalized_key and normalized_key in seen_names:
                errors = [BATCH_DUPLICATE_REASON]
                status = ImportRowStatus.INVALID
            elif normalized_key:
                seen_names[normalized_key] = row_number

        validated.append(
            ValidatedRow(
                row_number=row_number,
                raw=raw,
                normalized=normalized,
                errors=errors,
                status=status,
            )
        )

    return validated


def apply_participation_and_status(
    *,
    validated_rows: list[ValidatedRow],
    customer_index: CustomerMatchIndex,
    fair_id: UUID | None,
    participation_by_customer: dict[UUID, UUID] | None = None,
    participation_exists: Callable[[UUID], tuple[bool, UUID | None]] | None = None,
) -> list[tuple[ValidatedRow, dict[str, Any]]]:
    """Steps 6–7 — Match customer names and check participation for matched rows."""
    results: list[tuple[ValidatedRow, dict[str, Any]]] = []

    for row in validated_rows:
        match_fields: dict[str, Any] = {
            "match_customer_id": None,
            "match_confidence": None,
            "match_reason": None,
            "match_explanation": None,
            "participation_exists": None,
            "match_participation_id": None,
            "suggested_action": None,
            "status": row.status,
        }

        if row.status == ImportRowStatus.INVALID:
            match_fields["suggested_action"] = ImportSuggestedAction.SKIP
            results.append((row, match_fields))
            continue

        normalized_key = row.normalized.get("normalized_company_name") or ""
        raw_name = row.normalized.get("company_name") or ""
        if not normalized_key and raw_name:
            normalized_key = normalize_import_company_name(raw_name)
        match = find_customer_match(normalized_key, customer_index, raw_company_name=raw_name)

        if match is None:
            match_fields["match_reason"] = MATCH_TYPE_NO_MATCH
            match_fields["status"] = ImportRowStatus.READY_TO_CREATE
            match_fields["suggested_action"] = ImportSuggestedAction.CREATE_CUSTOMER_AND_PARTICIPATION
            match_fields["participation_exists"] = False
        elif match.reason in (MATCH_TYPE_FUZZY, MATCH_TYPE_WEAK):
            match_fields["match_customer_id"] = match.customer_id
            match_fields["match_confidence"] = match.confidence
            match_fields["match_reason"] = match.reason
            match_fields["match_explanation"] = match.explanation
            match_fields["status"] = ImportRowStatus.POSSIBLE_DUPLICATE
            match_fields["suggested_action"] = ImportSuggestedAction.LINK_EXISTING_CUSTOMER_TO_FAIR
            _apply_participation(
                match_fields,
                match.customer_id,
                fair_id,
                participation_by_customer,
                participation_exists,
            )
        else:
            match_fields["match_customer_id"] = match.customer_id
            match_fields["match_confidence"] = match.confidence
            match_fields["match_reason"] = MATCH_TYPE_EXACT
            match_fields["match_explanation"] = match.explanation
            if fair_id:
                _apply_participation(
                    match_fields,
                    match.customer_id,
                    fair_id,
                    participation_by_customer,
                    participation_exists,
                )
                if match_fields["participation_exists"]:
                    match_fields["suggested_action"] = ImportSuggestedAction.UPDATE_PARTICIPATION
                    match_fields["status"] = ImportRowStatus.READY_TO_UPDATE
                else:
                    match_fields["suggested_action"] = ImportSuggestedAction.LINK_EXISTING_CUSTOMER_TO_FAIR
                    match_fields["status"] = ImportRowStatus.READY_TO_UPDATE
            else:
                match_fields["status"] = ImportRowStatus.POSSIBLE_DUPLICATE
                match_fields["suggested_action"] = ImportSuggestedAction.LINK_EXISTING_CUSTOMER_TO_FAIR

        results.append((row, match_fields))

    return results


def _apply_participation(
    match_fields: dict[str, Any],
    customer_id: UUID,
    fair_id: UUID | None,
    participation_by_customer: dict[UUID, UUID] | None,
    participation_exists: Callable[[UUID], tuple[bool, UUID | None]] | None,
) -> None:
    if fair_id is None:
        return
    if participation_by_customer is not None:
        part_id = participation_by_customer.get(customer_id)
        match_fields["participation_exists"] = part_id is not None
        match_fields["match_participation_id"] = part_id
    elif participation_exists:
        exists, part_id = participation_exists(customer_id)
        match_fields["participation_exists"] = exists
        match_fields["match_participation_id"] = part_id
    else:
        match_fields["participation_exists"] = False
        match_fields["match_participation_id"] = None


def build_import_rows(
    *,
    batch: ImportBatch,
    raw_rows: list[dict[str, Any]],
    customers: list[Customer] | None = None,
    customer_index: CustomerMatchIndex | None = None,
    fair_id: UUID | None,
    participation_by_customer: dict[UUID, UUID] | None = None,
    participation_exists: Callable[[UUID], tuple[bool, UUID | None]] | None = None,
    now: datetime,
) -> list[ImportRow]:
    if customer_index is None:
        customer_index = CustomerMatchIndex.build(customers or [])

    validated = validate_mapped_rows(raw_rows)
    matched = apply_participation_and_status(
        validated_rows=validated,
        customer_index=customer_index,
        fair_id=fair_id,
        participation_by_customer=participation_by_customer,
        participation_exists=participation_exists,
    )

    rows: list[ImportRow] = []
    for row, match_fields in matched:
        normalized = dict(row.normalized)
        if match_fields.get("match_explanation"):
            normalized["_match_explanation"] = match_fields["match_explanation"]
        rows.append(
            ImportRow.create(
                batch_id=batch.id,
                organization_id=batch.organization_id,
                row_number=row.row_number,
                raw_data_json=row.raw,
                normalized_data_json=normalized,
                status=match_fields["status"],
                validation_errors_json=row.errors or None,
                match_customer_id=match_fields["match_customer_id"],
                match_confidence=match_fields["match_confidence"],
                match_reason=match_fields["match_reason"],
                participation_exists=match_fields["participation_exists"],
                match_participation_id=match_fields["match_participation_id"],
                suggested_action=match_fields["suggested_action"],
                now=now,
            )
        )

    return rows
