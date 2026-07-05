"""Excel export for scraper handoff review and comparison."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from openpyxl import Workbook

from app.modules.scraper.domain.requested_output_fields import (
    FIELD_TO_CANONICAL,
    FIELD_TO_METADATA,
    normalize_requested_fields,
)
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.shared.canonical_import.schema import CanonicalImportRow
from app.shared.canonical_import.scraper_mapper import scraper_handoff_to_canonical

EXCEL_COLUMNS: tuple[str, ...] = (
    "company_name",
    "normalized_company_name",
    "country",
    "city",
    "hall",
    "stand",
    "website",
    "email",
    "phone",
    "address",
    "category",
    "description",
    "source_url",
    "detail_scraped",
    "website_valid",
    "instagram_url",
    "linkedin_url",
    "facebook_url",
    "youtube_url",
    "x_url",
)

_NOTES_EXCEL_COLUMN = "description"
_VALID_EXCEL_COLUMNS: frozenset[str] = frozenset(EXCEL_COLUMNS)


def excel_columns_for_requested_fields(requested_fields: list[str] | None) -> tuple[str, ...]:
    """Return Excel header columns in requested-field order."""
    columns: list[str] = []
    seen: set[str] = set()
    for field in normalize_requested_fields(requested_fields):
        if field == "notes":
            candidate = _NOTES_EXCEL_COLUMN
        elif field in FIELD_TO_CANONICAL:
            candidate = FIELD_TO_CANONICAL[field]
        elif field in FIELD_TO_METADATA:
            candidate = FIELD_TO_METADATA[field]
        else:
            continue
        if candidate not in _VALID_EXCEL_COLUMNS or candidate in seen:
            continue
        columns.append(candidate)
        seen.add(candidate)
    return tuple(columns)


def _resolve_adapter_key(handoff: ScraperImportHandoff, adapter_key: str | None) -> str:
    if adapter_key:
        return adapter_key.strip()
    metadata = handoff.metadata or {}
    resolved = metadata.get("source_site") or metadata.get("adapter_key") or metadata.get("adapter_name")
    if resolved:
        return str(resolved).strip()
    return "tuyap_new"


def _canonical_import_row_to_excel_dict(row: CanonicalImportRow) -> dict[str, str]:
    """Map canonical import row to Excel cells (same values as JSON export)."""
    raw = row.raw or {}
    return {
        "company_name": row.company_name,
        "normalized_company_name": row.normalized_company_name,
        "country": row.country or "",
        "city": row.city or "",
        "hall": row.hall or "",
        "stand": row.stand or "",
        "website": row.website or "",
        "email": row.emails[0] if row.emails else "",
        "phone": row.phones[0] if row.phones else "",
        "address": str(raw.get("address") or ""),
        "category": str(raw.get("category") or ""),
        "description": str(raw.get("description") or raw.get("notes") or ""),
        "source_url": str(raw.get("source_url") or ""),
        "detail_scraped": _format_bool(raw.get("detail_scraped")),
        "website_valid": _format_bool(raw.get("website_valid")),
        "instagram_url": row.instagram_url or "",
        "facebook_url": row.facebook_url or "",
        "linkedin_url": row.linkedin_url or "",
        "youtube_url": row.youtube_url or "",
        "x_url": str(raw.get("x_url") or ""),
    }


def build_excel_rows(
    handoff: ScraperImportHandoff,
    *,
    columns: tuple[str, ...] | None = None,
    adapter_key: str | None = None,
    run_id: UUID | None = None,
    fair_id: UUID | None = None,
    source_url: str | None = None,
) -> list[dict[str, str]]:
    selected_columns = columns or EXCEL_COLUMNS
    document = scraper_handoff_to_canonical(
        handoff,
        adapter_key=_resolve_adapter_key(handoff, adapter_key),
        run_id=run_id,
        fair_id=fair_id,
        source_url=source_url,
    )
    rows: list[dict[str, str]] = []
    for row in document.rows:
        full_row = _canonical_import_row_to_excel_dict(row)
        rows.append({column: full_row.get(column, "") for column in selected_columns})
    return rows


def _format_bool(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def write_handoff_excel(
    handoff: ScraperImportHandoff,
    output_path: str,
    *,
    requested_fields: list[str] | None = None,
    adapter_key: str | None = None,
    run_id: UUID | None = None,
    fair_id: UUID | None = None,
    source_url: str | None = None,
) -> Path:
    path = Path(output_path)
    if requested_fields is None:
        columns = EXCEL_COLUMNS
    else:
        columns = excel_columns_for_requested_fields(requested_fields)
        if not columns:
            columns = ("company_name",)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "companies"

    sheet.append(list(columns))
    for row in build_excel_rows(
        handoff,
        columns=columns,
        adapter_key=adapter_key,
        run_id=run_id,
        fair_id=fair_id,
        source_url=source_url,
    ):
        sheet.append([row.get(column, "") for column in columns])

    workbook.save(path)
    return path.resolve()
