"""Tests for scraper handoff Excel exporter."""

from pathlib import Path

from openpyxl import load_workbook

from app.modules.scraper.exporters.scraper_excel_exporter import (
    EXCEL_COLUMNS,
    excel_columns_for_requested_fields,
    write_handoff_excel,
)
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff


def test_write_handoff_excel_writes_expected_headers(tmp_path: Path):
    handoff = ScraperImportHandoff(
        canonical_rows=[
            {
                "company_name": "Acme",
                "country": "Türkiye",
                "hall": "1",
                "stand": "A1",
            }
        ],
        metadata={"fair_name": "Foodist Expo"},
        row_metadata=[
            {
                "source_url": "https://example.test/brand/acme",
                "category": "Gıda",
                "detail_scraped": True,
                "website_valid": True,
            }
        ],
    )

    path = write_handoff_excel(handoff, str(tmp_path / "companies.xlsx"))
    workbook = load_workbook(path)
    sheet = workbook.active
    assert [cell.value for cell in sheet[1]] == list(EXCEL_COLUMNS)


def test_write_handoff_excel_filters_columns_by_requested_fields(tmp_path: Path):
    handoff = ScraperImportHandoff(
        canonical_rows=[
            {
                "company_name": "Acme",
                "phone": "555",
                "email": "a@b.com",
                "website": "https://acme.test",
            }
        ],
        row_metadata=[{}],
    )
    requested = ["customerName", "phone", "email"]
    columns = excel_columns_for_requested_fields(requested)
    assert columns == ("company_name", "phone", "email")

    path = write_handoff_excel(
        handoff,
        str(tmp_path / "filtered.xlsx"),
        requested_fields=requested,
    )
    workbook = load_workbook(path)
    sheet = workbook.active
    assert [cell.value for cell in sheet[1]] == list(columns)
    assert [cell.value for cell in sheet[2]] == ["Acme", "555", "a@b.com"]
