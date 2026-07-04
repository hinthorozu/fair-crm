"""Tests for scraper → Import Engine handoff exporter."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportExporter
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.types.scraper_result import ScraperResult
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _build_scraper_result() -> ScraperResult:
    raw = RawCompanyDto(
        company_name="2A AKÜZÜM OTOMOTİV A.Ş.",
        country="Türkiye",
        hall="12",
        stand="1232A",
        email="info@akuzum.test",
        phone="0212 444 55 66",
        website="https://www.akuzum.test",
        source_url="https://foodist.tuyap.online/brand/2a-akuzum",
        metadata={"detail_url": "https://foodist.tuyap.online/brand/2a-akuzum", "placeholder": False},
    )
    normalizer = CompanyNormalizer()
    normalized = normalizer.normalize(raw)
    assert normalized is not None

    return ScraperResult(
        site_key=ScraperSiteKey.TUYAP_NEW,
        fair_id=uuid4(),
        companies=[normalized],
        raw_count=1,
        normalized_count=1,
        metadata={
            "adapter": "TÜYAP (New)",
            "list_url": "https://foodist.tuyap.online/brands",
        },
        scraped_at=datetime.now(UTC),
    )


def test_exporter_raw_to_normalized_to_canonical_row():
    result = _build_scraper_result()
    handoff = ScraperImportExporter().export(
        result,
        fair_name="Foodist Expo",
        fair_year=2026,
        source_url="https://foodist.tuyap.online/brands",
    )

    assert len(handoff.canonical_rows) == 1
    row = handoff.canonical_rows[0]
    assert row["company_name"] == "2A AKÜZÜM OTOMOTİV A.Ş."
    assert row["country"] == "Türkiye"
    assert row["hall"] == "12"
    assert row["stand"] == "1232A"
    assert row["email"] == "info@akuzum.test"
    assert row["phone"] == "0212 444 55 66"
    assert row["website"] == "https://www.akuzum.test"


def test_exporter_preserves_batch_metadata():
    result = _build_scraper_result()
    handoff = ScraperImportExporter().export(
        result,
        fair_name="Foodist Expo",
        fair_year=2026,
        source_url="https://foodist.tuyap.online/brands",
    )

    assert handoff.metadata["fair_name"] == "Foodist Expo"
    assert handoff.metadata["fair_year"] == 2026
    assert handoff.metadata["source_site"] == ScraperSiteKey.TUYAP_NEW
    assert handoff.metadata["source_url"] == "https://foodist.tuyap.online/brands"
    assert handoff.metadata["adapter_name"] == "TÜYAP (New)"
    assert handoff.metadata["normalized_count"] == 1


def test_exporter_carries_row_source_url_and_adapter_metadata():
    result = _build_scraper_result()
    handoff = ScraperImportExporter().export(result)

    assert len(handoff.row_metadata) == 1
    row_meta = handoff.row_metadata[0]
    assert row_meta["source_url"] == "https://foodist.tuyap.online/brand/2a-akuzum"
    assert row_meta["adapter_name"] == "TÜYAP (New)"
    assert row_meta["detail_url"] == "https://foodist.tuyap.online/brand/2a-akuzum"
