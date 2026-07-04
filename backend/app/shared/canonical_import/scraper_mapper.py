"""Map scraper handoff payloads to the canonical import document."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.modules.imports.domain.services.company_name_normalizer import normalize_import_company_name
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.shared.canonical_import.schema import (
    CanonicalImportDocument,
    CanonicalImportMetadata,
    CanonicalImportRow,
    CanonicalImportSource,
    CanonicalImportSourceType,
)

_EMAIL_FIELDS = ("email", "contact_email")
_PHONE_FIELDS = ("phone", "mobile_phone", "contact_phone", "contact_mobile_phone")
_ROW_TOP_LEVEL_FIELDS = frozenset(
    {
        "company_name",
        "website",
        "country",
        "city",
        "hall",
        "stand",
        *_EMAIL_FIELDS,
        *_PHONE_FIELDS,
    }
)


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _collect_values(row: dict[str, Any], *keys: str) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()
    for key in keys:
        value = _clean_str(row.get(key))
        if value is None or value in seen:
            continue
        seen.add(value)
        collected.append(value)
    return collected


def _build_raw_payload(
    canonical_row: dict[str, str],
    row_metadata: dict[str, Any],
) -> dict[str, Any]:
    raw: dict[str, Any] = dict(row_metadata)
    for key, value in canonical_row.items():
        if key in _ROW_TOP_LEVEL_FIELDS:
            continue
        cleaned = _clean_str(value)
        if cleaned is not None:
            raw.setdefault(key, cleaned)
    return raw


def _map_row(canonical_row: dict[str, str], row_metadata: dict[str, Any]) -> CanonicalImportRow:
    company_name = _clean_str(canonical_row.get("company_name")) or ""
    return CanonicalImportRow(
        external_id=_clean_str(row_metadata.get("external_id")),
        company_name=company_name,
        normalized_company_name=normalize_import_company_name(company_name),
        website=_clean_str(canonical_row.get("website")),
        emails=_collect_values(canonical_row, *_EMAIL_FIELDS),
        phones=_collect_values(canonical_row, *_PHONE_FIELDS),
        country=_clean_str(canonical_row.get("country")),
        city=_clean_str(canonical_row.get("city")),
        hall=_clean_str(canonical_row.get("hall")),
        stand=_clean_str(canonical_row.get("stand")),
        raw=_build_raw_payload(canonical_row, row_metadata),
    )


def scraper_handoff_to_canonical(
    handoff: ScraperImportHandoff,
    *,
    adapter_key: str,
    run_id: UUID | None = None,
    fair_id: UUID | None = None,
    source_url: str | None = None,
    created_at: datetime | None = None,
) -> CanonicalImportDocument:
    metadata = handoff.metadata or {}
    resolved_fair_id = fair_id
    if resolved_fair_id is None and metadata.get("fair_id"):
        resolved_fair_id = UUID(str(metadata["fair_id"]))

    resolved_source_url = source_url or _clean_str(metadata.get("source_url"))
    resolved_adapter_key = (adapter_key or _clean_str(metadata.get("source_site")) or "").strip()
    row_metadata = handoff.row_metadata or []
    padded_metadata = row_metadata + [{}] * max(0, len(handoff.canonical_rows or []) - len(row_metadata))

    rows = [
        _map_row(canonical_row, padded_metadata[index])
        for index, canonical_row in enumerate(handoff.canonical_rows or [])
    ]

    created = created_at or datetime.now(UTC)
    if metadata.get("scraped_at") and created_at is None:
        try:
            created = datetime.fromisoformat(str(metadata["scraped_at"]))
        except ValueError:
            created = datetime.now(UTC)

    return CanonicalImportDocument(
        source=CanonicalImportSource(
            type=CanonicalImportSourceType.SCRAPER,
            adapter_key=resolved_adapter_key,
            fair_id=resolved_fair_id,
            run_id=run_id,
            source_url=resolved_source_url,
        ),
        metadata=CanonicalImportMetadata(
            created_at=created,
            row_count=len(rows),
        ),
        rows=rows,
    )
