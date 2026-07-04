"""Tests for requested output field normalization and handoff filtering."""

from app.modules.scraper.domain.requested_output_fields import (
    DEFAULT_REQUESTED_FIELDS,
    filter_handoff_by_requested_fields,
    needs_detail_scrape,
    normalize_requested_fields,
)
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff


def test_normalize_requested_fields_defaults_when_empty() -> None:
    assert normalize_requested_fields(None) == list(DEFAULT_REQUESTED_FIELDS)
    assert normalize_requested_fields([]) == list(DEFAULT_REQUESTED_FIELDS)


def test_normalize_requested_fields_deduplicates_and_filters_invalid() -> None:
    assert normalize_requested_fields(
        ["customerName", "website", "website", "invalid", "instagram"]
    ) == ["customerName", "website", "instagram"]


def test_needs_detail_scrape_only_list_fields() -> None:
    assert needs_detail_scrape(["customerName", "hall", "stand"]) is False


def test_needs_detail_scrape_when_detail_field_requested() -> None:
    assert needs_detail_scrape(["customerName", "website"]) is True
    assert needs_detail_scrape(["customerName", "instagram"]) is True


def test_filter_handoff_removes_unrequested_fields() -> None:
    handoff = ScraperImportHandoff(
        canonical_rows=[
            {
                "company_name": "ABC Firma",
                "website": "https://abc.com",
                "email": "info@abc.com",
                "phone": "555",
            }
        ],
        row_metadata=[
            {
                "instagram_url": "https://instagram.com/abc",
                "facebook_url": "https://facebook.com/abc",
            }
        ],
    )

    filtered = filter_handoff_by_requested_fields(
        handoff,
        ["customerName", "website", "instagram"],
    )

    row = filtered.canonical_rows[0]
    assert set(row.keys()) == {"company_name", "website"}
    assert row["company_name"] == "ABC Firma"
    assert "email" not in row
    assert "phone" not in row

    meta = filtered.row_metadata[0]
    assert set(meta.keys()) == {"instagram_url"}
    assert "facebook_url" not in meta


def test_filter_handoff_customer_name_only() -> None:
    handoff = ScraperImportHandoff(
        canonical_rows=[{"company_name": "Only Name", "hall": "1", "stand": "A"}],
        row_metadata=[{"instagram_url": "https://instagram.com/x"}],
    )

    filtered = filter_handoff_by_requested_fields(handoff, ["customerName"])
    assert filtered.canonical_rows == [{"company_name": "Only Name"}]
    assert filtered.row_metadata == [{}]


def test_output_field_capabilities_from_supports() -> None:
    from app.modules.scraper.domain.requested_output_fields import output_field_capabilities_from_supports
    from app.modules.scraper.manifests.scraper_manifest import ScraperSupports

    supports = ScraperSupports(
        list_scraping=True,
        detail_scraping=True,
        pagination=True,
        website=True,
        email=True,
        phone=True,
        address=True,
        category=True,
        description=True,
    )
    caps = output_field_capabilities_from_supports(supports)

    assert caps["customerName"] is True
    assert caps["website"] is True
    assert caps["email"] is True
    assert caps["instagram"] is True
    assert caps["notes"] is True
    assert "category" not in caps
    assert "list_scraping" not in caps
