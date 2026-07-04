"""Tests for scraper handoff → canonical import mapping."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from app.shared.canonical_import.scraper_mapper import scraper_handoff_to_canonical
from app.shared.canonical_import.validator import validate_canonical_import


def test_scraper_handoff_to_canonical_maps_rows_and_source():
    fair_id = uuid4()
    run_id = uuid4()
    handoff = ScraperImportHandoff(
        canonical_rows=[
            {
                "company_name": "ABC LTD",
                "website": "https://abc.com",
                "email": "info@abc.com",
                "phone": "+902121112233",
                "country": "Türkiye",
                "city": "İstanbul",
                "hall": "2",
                "stand": "A-12",
                "address": "Fuar Merkezi",
            }
        ],
        metadata={
            "source_site": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://foodist.test/brands",
            "fair_id": str(fair_id),
            "scraped_at": datetime(2026, 7, 4, 12, 0, tzinfo=UTC).isoformat(),
        },
        row_metadata=[
            {
                "source_url": "https://foodist.test/brand/abc",
                "category": "Gıda",
            }
        ],
    )

    document = scraper_handoff_to_canonical(
        handoff,
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        run_id=run_id,
        fair_id=fair_id,
        source_url="https://foodist.test/brands",
    )
    validated = validate_canonical_import(document)

    assert validated.source.type.value == "scraper"
    assert validated.source.adapter_key == ScraperSiteKey.TUYAP_NEW
    assert validated.source.fair_id == fair_id
    assert validated.source.run_id == run_id
    assert validated.source.source_url == "https://foodist.test/brands"
    assert validated.metadata.row_count == 1
    row = validated.rows[0]
    assert row.company_name == "ABC LTD"
    assert row.normalized_company_name == "abc"
    assert row.emails == ["info@abc.com"]
    assert row.phones == ["+902121112233"]
    assert row.raw["category"] == "Gıda"
    assert row.raw["source_url"] == "https://foodist.test/brand/abc"
    assert row.raw["address"] == "Fuar Merkezi"


def test_scraper_handoff_to_canonical_deduplicates_emails_and_phones():
    handoff = ScraperImportHandoff(
        canonical_rows=[
            {
                "company_name": "Dup Co",
                "email": "info@dup.test",
                "contact_email": "info@dup.test",
                "phone": "111",
                "mobile_phone": "111",
            }
        ],
        row_metadata=[{}],
    )

    document = scraper_handoff_to_canonical(
        handoff,
        adapter_key=ScraperSiteKey.TUYAP_NEW,
    )

    row = document.rows[0]
    assert row.emails == ["info@dup.test"]
    assert row.phones == ["111"]
