"""Tests for Foodist scraper runner script."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.run_foodist_scraper import (  # noqa: E402
    build_parser,
    handoff_to_dict,
    parse_args,
    run_pipeline,
    scrape_and_export,
    write_handoff_json,
)
from app.modules.scraper.adapters.tuyap_new_adapter import TuyapNewAdapter
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.exporters.scraper_excel_exporter import EXCEL_COLUMNS, write_handoff_excel
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.types.scraper_context import ScraperContext


async def _mock_scrape_async(context: ScraperContext) -> list[RawCompanyDto]:
    return _MockFoodistAdapter().scrape(context)


class _MockFoodistAdapter:
    site_key = "tuyap_new"
    display_name = "TÜYAP (New)"

    def scrape(self, context: ScraperContext) -> list[RawCompanyDto]:
        return [
            RawCompanyDto(
                company_name="Foodist Demo Co",
                country="Türkiye",
                city="İstanbul",
                hall="3",
                stand="A10",
                email="info@foodist-demo.test",
                phone="0212 111 22 33",
                website="https://www.foodist-demo.test",
                address="Fuar Merkezi",
                source_url="https://foodist.tuyap.online/brand/foodist-demo",
                metadata={"detail_url": "https://foodist.tuyap.online/brand/foodist-demo"},
                extra_fields={"category": "Gıda", "description": "Demo açıklama."},
            )
        ]


def test_build_parser_accepts_expected_arguments():
    args = parse_args(
        [
            "--url",
            "https://www.foodistexpo.com/katilimci-listesi",
            "--fair-name",
            "Foodist Expo",
            "--fair-year",
            "2026",
            "--max-pages",
            "10",
            "--scrape-detail",
            "--output",
            "foodist_handoff.json",
            "--excel-output",
            "foodist_companies.xlsx",
        ]
    )

    assert args.url == "https://www.foodistexpo.com/katilimci-listesi"
    assert args.fair_name == "Foodist Expo"
    assert args.fair_year == 2026
    assert args.max_pages == 10
    assert args.scrape_detail is True
    assert args.output == "foodist_handoff.json"
    assert args.excel_output == "foodist_companies.xlsx"


def test_build_parser_max_pages_optional():
    args = parse_args(["--url", "https://www.foodistexpo.com/katilimci-listesi"])
    assert args.max_pages is None


def test_build_parser_requires_url():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


@pytest.mark.asyncio
async def test_run_pipeline_with_mock_adapter_produces_handoff_json(tmp_path: Path):
    args = parse_args(
        [
            "--url",
            "https://www.foodistexpo.com/katilimci-listesi",
            "--fair-name",
            "Foodist Expo",
            "--fair-year",
            "2026",
            "--max-pages",
            "2",
        ]
    )
    adapter = TuyapNewAdapter(browser=None)
    adapter.scrape_async = _mock_scrape_async  # type: ignore[method-assign]

    handoff = await scrape_and_export(args, adapter=adapter)
    output_path = tmp_path / "foodist_handoff.json"
    text = write_handoff_json(handoff, str(output_path))
    payload = json.loads(text)

    assert output_path.exists()
    assert payload["source"]["type"] == "scraper"
    assert payload["source"]["adapter_key"] == "tuyap_new"
    assert payload["source"]["source_url"] == "https://www.foodistexpo.com/katilimci-listesi"
    assert payload["metadata"]["row_count"] == 1
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["company_name"] == "Foodist Demo Co"
    assert payload["rows"][0]["emails"] == ["info@foodist-demo.test"]
    assert payload["rows"][0]["phones"] == ["0212 111 22 33"]
    assert payload["rows"][0]["website"] == "https://www.foodist-demo.test"
    assert payload["rows"][0]["hall"] == "3"
    assert payload["rows"][0]["stand"] == "A10"
    assert payload["rows"][0]["raw"]["source_url"] == "https://foodist.tuyap.online/brand/foodist-demo"


def test_scrape_and_export_with_mock_adapter():
    args = parse_args(
        [
            "--url",
            "https://www.foodistexpo.com/katilimci-listesi",
            "--fair-name",
            "Foodist Expo",
            "--fair-year",
            "2026",
        ]
    )
    adapter = TuyapNewAdapter(browser=None)
    adapter.scrape_async = _mock_scrape_async  # type: ignore[method-assign]

    handoff = asyncio.run(scrape_and_export(args, adapter=adapter))
    payload = handoff_to_dict(handoff)

    assert isinstance(handoff, ScraperImportHandoff)
    assert payload["source"]["adapter_key"] == "tuyap_new"
    assert payload["rows"][0]["company_name"] == "Foodist Demo Co"


def test_write_handoff_excel_creates_file_with_expected_columns(tmp_path: Path):
    args = parse_args(
        [
            "--url",
            "https://www.foodistexpo.com/katilimci-listesi",
            "--fair-name",
            "Foodist Expo",
            "--fair-year",
            "2026",
        ]
    )
    adapter = TuyapNewAdapter(browser=None)
    adapter.scrape_async = _mock_scrape_async  # type: ignore[method-assign]
    handoff = asyncio.run(scrape_and_export(args, adapter=adapter))

    excel_path = tmp_path / "foodist_companies.xlsx"
    write_handoff_excel(handoff, str(excel_path))

    assert excel_path.exists()
    workbook = load_workbook(excel_path)
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    assert headers == list(EXCEL_COLUMNS)

    values = [cell.value for cell in sheet[2]]
    assert values[0] == "Foodist Demo Co"
    assert values[1] == "Foodist Demo Co"
    assert values[2] == "Türkiye"
    assert values[3] == "İstanbul"
    assert values[4] == "3"
    assert values[5] == "A10"
    assert values[6] == "https://www.foodist-demo.test"
    assert values[7] == "info@foodist-demo.test"
    assert values[8] == "0212 111 22 33"
    assert values[9] == "Fuar Merkezi"
    assert values[10] == "Gıda"
    assert values[11] == "Demo açıklama."
    assert values[12] == "https://foodist.tuyap.online/brand/foodist-demo"
    assert values[13] in (None, "", "false")
    assert values[14] in (None, "", "false")
