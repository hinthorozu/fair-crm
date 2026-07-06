"""Import row matching for customer contact enrichment batches."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.import_row_builder import ValidatedRow
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSuggestedAction
from app.modules.scraper.domain.enrichment_adapter import MATCH_REASON_ENRICHMENT_CUSTOMER_ID


def apply_enrichment_customer_id_matches(
    *,
    validated_rows: list[ValidatedRow],
    organization_id: UUID,
    customer_repository: CustomerRepository,
) -> list[tuple[ValidatedRow, dict[str, Any]]]:
    results: list[tuple[ValidatedRow, dict[str, Any]]] = []

    for row in validated_rows:
        match_fields: dict[str, Any] = {
            "match_customer_id": None,
            "match_confidence": None,
            "match_reason": None,
            "match_explanation": None,
            "participation_exists": False,
            "match_participation_id": None,
            "suggested_action": ImportSuggestedAction.SKIP,
            "status": row.status,
        }

        if row.status == ImportRowStatus.INVALID:
            results.append((row, match_fields))
            continue

        customer_id_raw = row.normalized.get("external_id") or row.raw.get("external_id")
        try:
            customer_id = UUID(str(customer_id_raw))
        except (TypeError, ValueError):
            match_fields["status"] = ImportRowStatus.INVALID
            match_fields["suggested_action"] = ImportSuggestedAction.SKIP
            results.append((row, match_fields))
            continue

        customer = customer_repository.get_by_id(organization_id, customer_id)
        if customer is None:
            match_fields["status"] = ImportRowStatus.INVALID
            match_fields["suggested_action"] = ImportSuggestedAction.SKIP
            results.append((row, match_fields))
            continue

        match_fields.update(
            {
                "match_customer_id": customer_id,
                "match_confidence": 100,
                "match_reason": MATCH_REASON_ENRICHMENT_CUSTOMER_ID,
                "match_explanation": "Enrichment customer_id binding",
                "participation_exists": False,
                "match_participation_id": None,
                "suggested_action": ImportSuggestedAction.LINK_EXISTING_CUSTOMER_TO_FAIR,
                "status": ImportRowStatus.READY_TO_UPDATE,
            }
        )
        results.append((row, match_fields))

    return results


def resolve_adapter_key_from_batch_preview(raw_preview_json: dict[str, Any] | None) -> str | None:
    preview = raw_preview_json or {}
    source = preview.get("canonical_source") or {}
    adapter_key = source.get("adapter_key")
    return str(adapter_key).strip() if adapter_key else None
