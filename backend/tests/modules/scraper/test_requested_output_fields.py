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


def test_filter_handoff_preserves_enrichment_identity_metadata() -> None:
    handoff = ScraperImportHandoff(
        canonical_rows=[{"company_name": "Target Co", "email": "info@target.test"}],
        row_metadata=[
            {
                "external_id": "00000000-0000-0000-0000-000000000001",
                "customer_id": "00000000-0000-0000-0000-000000000001",
                "enrichment_status": "found",
                "email_source_url": "https://target.test/contact",
                "instagram_url": "https://instagram.com/target",
            }
        ],
    )

    filtered = filter_handoff_by_requested_fields(handoff, ["email"])

    meta = filtered.row_metadata[0]
    assert meta["external_id"] == "00000000-0000-0000-0000-000000000001"
    assert meta["customer_id"] == "00000000-0000-0000-0000-000000000001"
    assert meta["enrichment_status"] == "found"
    assert meta["email_source_url"] == "https://target.test/contact"
    assert "instagram_url" not in meta


def test_filter_handoff_preserves_social_source_urls() -> None:
    handoff = ScraperImportHandoff(
        canonical_rows=[{"company_name": "Target Co", "email": "info@target.test"}],
        row_metadata=[
            {
                "external_id": "00000000-0000-0000-0000-000000000002",
                "customer_id": "00000000-0000-0000-0000-000000000002",
                "instagram_url": "https://instagram.com/target",
                "instagram_source_url": "https://target.test/contact",
            }
        ],
    )

    filtered = filter_handoff_by_requested_fields(handoff, ["email"])

    meta = filtered.row_metadata[0]
    assert meta["external_id"] == "00000000-0000-0000-0000-000000000002"
    assert meta["instagram_source_url"] == "https://target.test/contact"
    assert "instagram_url" not in meta


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


def test_default_requested_fields_for_capabilities_tuyap_old() -> None:
    from app.modules.scraper.domain.requested_output_fields import (
        default_requested_fields_for_capabilities,
        output_field_capabilities_from_supports,
    )
    from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST

    caps = output_field_capabilities_from_supports(TUYAP_OLD_MANIFEST.supports)
    assert default_requested_fields_for_capabilities(caps) == [
        "customerName",
        "phone",
        "email",
        "address",
        "website",
        "hall",
        "stand",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
        "notes",
    ]


def test_filter_requested_fields_by_capabilities_drops_unsupported() -> None:
    from app.modules.scraper.domain.requested_output_fields import (
        filter_requested_fields_by_capabilities,
        output_field_capabilities_from_supports,
    )
    from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST

    caps = output_field_capabilities_from_supports(TUYAP_OLD_MANIFEST.supports)
    assert filter_requested_fields_by_capabilities(
        ["customerName", "email", "instagram", "notes"],
        caps,
    ) == ["customerName", "email", "instagram", "notes"]


def test_resolve_requested_fields_for_manifest_uses_capability_defaults() -> None:
    from app.modules.scraper.domain.requested_output_fields import resolve_requested_fields_for_manifest
    from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST

    assert resolve_requested_fields_for_manifest(None, TUYAP_OLD_MANIFEST.supports) == [
        "customerName",
        "phone",
        "email",
        "address",
        "website",
        "hall",
        "stand",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
        "notes",
    ]


def test_normalize_requested_fields_filters_by_capabilities() -> None:
    from app.modules.scraper.domain.requested_output_fields import (
        normalize_requested_fields,
        output_field_capabilities_from_supports,
    )
    from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST

    caps = output_field_capabilities_from_supports(TUYAP_OLD_MANIFEST.supports)
    assert normalize_requested_fields(
        ["customerName", "email", "instagram"],
        capabilities=caps,
    ) == ["customerName", "email", "instagram"]


def test_tuyap_old_output_field_capabilities_match_tuyap_new_contract() -> None:
    from app.modules.scraper.domain.requested_output_fields import output_field_capabilities_from_supports
    from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST

    caps = output_field_capabilities_from_supports(TUYAP_OLD_MANIFEST.supports)

    assert caps["email"] is True
    assert caps["notes"] is True
    assert caps["instagram"] is True
    assert caps["facebook"] is True
    assert caps["linkedin"] is True
    assert caps["youtube"] is True
