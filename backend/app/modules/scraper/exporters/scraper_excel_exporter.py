"""Excel export for scraper handoff review and comparison."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

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


def build_excel_rows(handoff: ScraperImportHandoff) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    row_metadata = handoff.row_metadata or []

    for index, canonical in enumerate(handoff.canonical_rows):
        meta = row_metadata[index] if index < len(row_metadata) else {}
        rows.append(
            {
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
        )
    return rows


def _format_bool(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def write_handoff_excel(handoff: ScraperImportHandoff, output_path: str) -> Path:
    path = Path(output_path)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "companies"

    sheet.append(list(EXCEL_COLUMNS))
    for row in build_excel_rows(handoff):
        sheet.append([row.get(column, "") for column in EXCEL_COLUMNS])

    workbook.save(path)
    return path.resolve()
