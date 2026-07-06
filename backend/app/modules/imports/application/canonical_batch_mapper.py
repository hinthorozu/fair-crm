"""Map canonical import documents to import batch + row entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSourceType
from app.modules.imports.domain.services.social_url_fields import social_urls_from_mapping
from app.shared.canonical_import.schema import CanonicalImportDocument, CanonicalImportRow

CANONICAL_TO_IMPORT_SOURCE: dict[str, ImportSourceType] = {
    "scraper": ImportSourceType.SCRAPER,
    "excel": ImportSourceType.EXCEL,
    "csv": ImportSourceType.CSV,
    "api": ImportSourceType.API,
}


def resolve_import_source_type(source_type: str) -> ImportSourceType:
    mapped = CANONICAL_TO_IMPORT_SOURCE.get(source_type)
    if mapped is None:
        raise ValueError(f"Unsupported canonical source type: {source_type}")
    return mapped


def resolve_canonical_file_name(document: CanonicalImportDocument) -> str:
    source = document.source
    if source.run_id is not None:
        prefix = (source.adapter_key or source.type.value).strip()
        return f"{prefix}-{source.run_id}.json"
    adapter = (source.adapter_key or "").strip()
    if adapter:
        return f"canonical-{adapter}.json"
    return f"canonical-{source.type.value}.json"


def build_batch_preview_json(document: CanonicalImportDocument) -> dict[str, Any]:
    return {
        "canonical_source": document.source.model_dump(mode="json"),
        "canonical_metadata": document.metadata.model_dump(mode="json"),
    }


def canonical_row_to_normalized(row: CanonicalImportRow) -> dict[str, Any]:
    emails = list(row.emails)
    phones = list(row.phones)
    normalized = {
        "company_name": row.company_name,
        "normalized_company_name": row.normalized_company_name,
        "website": row.website,
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "emails": emails,
        "phones": phones,
        "country": row.country,
        "city": row.city,
        "hall": row.hall,
        "stand": row.stand,
        "external_id": row.external_id,
        "instagram_url": row.instagram_url,
        "facebook_url": row.facebook_url,
        "linkedin_url": row.linkedin_url,
        "youtube_url": row.youtube_url,
    }
    normalized.update(
        {
            key: value
            for key, value in social_urls_from_mapping(row.raw).items()
            if value is not None and normalized.get(key) is None
        }
    )
    return normalized


def build_import_rows_from_canonical(
    document: CanonicalImportDocument,
    *,
    batch_id: UUID,
    organization_id: UUID,
    now: datetime,
) -> list[ImportRow]:
    rows: list[ImportRow] = []
    for index, canonical_row in enumerate(document.rows, start=1):
        rows.append(
            ImportRow.create(
                batch_id=batch_id,
                organization_id=organization_id,
                row_number=index,
                raw_data_json=canonical_row.model_dump(mode="json"),
                normalized_data_json=canonical_row_to_normalized(canonical_row),
                status=ImportRowStatus.VALID,
                validation_errors_json=None,
                match_customer_id=None,
                match_confidence=None,
                match_reason=None,
                now=now,
            )
        )
    return rows


def build_import_batch_from_canonical(
    document: CanonicalImportDocument,
    *,
    organization_id: UUID,
    fair_id: UUID | None,
    now: datetime,
) -> ImportBatch:
    row_count = len(document.rows)
    return ImportBatch.create_from_canonical(
        organization_id=organization_id,
        fair_id=fair_id,
        source_type=resolve_import_source_type(document.source.type.value),
        file_name=resolve_canonical_file_name(document),
        total_rows=row_count,
        valid_rows=row_count,
        invalid_rows=0,
        raw_preview_json=build_batch_preview_json(document),
        now=now,
    )
