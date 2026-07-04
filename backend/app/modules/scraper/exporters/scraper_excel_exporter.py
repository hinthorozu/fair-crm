"""Excel export for scraper handoff review and comparison."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from app.modules.scraper.domain.requested_output_fields import (
    FIELD_TO_CANONICAL,
    FIELD_TO_METADATA,
    normalize_requested_fields,
)
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff

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


def build_excel_rows(
    handoff: ScraperImportHandoff,
    *,
    columns: tuple[str, ...] | None = None,
) -> list[dict[str, str]]:
    selected_columns = columns or EXCEL_COLUMNS
    rows: list[dict[str, str]] = []
    row_metadata = handoff.row_metadata or []

    for index, canonical in enumerate(handoff.canonical_rows):
        meta = row_metadata[index] if index < len(row_metadata) else {}
        full_row = {
            "company_name": canonical.get("company_name", ""),
            "normalized_company_name": canonical.get("company_name", ""),
            "country": canonical.get("country", ""),
            "city": canonical.get("city", ""),
            "hall": canonical.get("hall", ""),
            "stand": canonical.get("stand", ""),
            "website": canonical.get("website", ""),
            "email": canonical.get("email", ""),
            "phone": canonical.get("phone", ""),
            "address": canonical.get("address", ""),
            "category": str(meta.get("category", "")),
            "description": str(meta.get("description", "")),
            "source_url": str(meta.get("source_url", "")),
            "detail_scraped": _format_bool(meta.get("detail_scraped")),
            "website_valid": _format_bool(meta.get("website_valid")),
            "instagram_url": str(meta.get("instagram_url", "")),
            "linkedin_url": str(meta.get("linkedin_url", "")),
            "facebook_url": str(meta.get("facebook_url", "")),
            "youtube_url": str(meta.get("youtube_url", "")),
            "x_url": str(meta.get("x_url", "")),
        }
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
    for row in build_excel_rows(handoff, columns=columns):
        sheet.append([row.get(column, "") for column in columns])

    workbook.save(path)
    return path.resolve()
