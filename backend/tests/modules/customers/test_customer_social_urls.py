"""Tests for customer social URL fields and import mapping."""

from uuid import uuid4

from app.modules.imports.domain.services.social_url_fields import resolve_social_url, social_urls_from_mapping
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportExporter
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.types.scraper_result import ScraperResult
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from app.shared.canonical_import.scraper_mapper import scraper_handoff_to_canonical
from app.shared.url_normalization import normalize_optional_url


def test_normalize_optional_url_adds_https_scheme():
    assert normalize_optional_url("instagram.com/acme") == "https://instagram.com/acme"
    assert normalize_optional_url("https://facebook.com/acme") == "https://facebook.com/acme"
    assert normalize_optional_url("") is None
    assert normalize_optional_url(None) is None


def test_resolve_social_url_accepts_short_and_long_keys():
    data = {"instagram": "instagram.com/acme", "linkedin_url": "https://linkedin.com/company/acme"}
    assert resolve_social_url(data, url_key="instagram_url", short_key="instagram") == (
        "https://instagram.com/acme"
    )
    assert resolve_social_url(data, url_key="linkedin_url", short_key="linkedin") == (
        "https://linkedin.com/company/acme"
    )


def test_company_normalizer_promotes_social_urls_from_extra_fields():
    raw = RawCompanyDto(
        company_name="Acme Gıda A.Ş.",
        extra_fields={
            "instagram_url": "https://www.instagram.com/acme/",
            "facebook_url": "https://www.facebook.com/acme",
        },
        metadata={"linkedin_url": "linkedin.com/company/acme", "youtube": "youtube.com/@acme"},
    )
    normalized = CompanyNormalizer().normalize(raw)
    assert normalized is not None
    assert normalized.instagram_url == "https://www.instagram.com/acme/"
    assert normalized.facebook_url == "https://www.facebook.com/acme"
    assert normalized.linkedin_url == "https://linkedin.com/company/acme"
    assert normalized.youtube_url == "https://youtube.com/@acme"

    row = normalized.to_canonical_row()
    assert row["instagram_url"] == "https://www.instagram.com/acme/"
    assert row["youtube_url"] == "https://youtube.com/@acme"


def test_scraper_handoff_to_canonical_promotes_social_urls_from_metadata():
    company = CompanyNormalizer().normalize(
        RawCompanyDto(
            company_name="Social Co",
            extra_fields={"instagram_url": "https://www.instagram.com/social/"},
        )
    )
    assert company is not None
    handoff = ScraperImportExporter().export(
        ScraperResult(
            site_key=ScraperSiteKey.TUYAP_NEW,
            fair_id=uuid4(),
            companies=[company],
            raw_count=1,
            normalized_count=1,
            metadata={"adapter": "TÜYAP (New)"},
        )
    )
    document = scraper_handoff_to_canonical(handoff, adapter_key=ScraperSiteKey.TUYAP_NEW)
    row = document.rows[0]
    assert row.instagram_url == "https://www.instagram.com/social/"
    assert row.company_name == "Social Co"


def test_social_urls_from_mapping_prefers_url_key_over_short_key():
    data = {
        "instagram": "instagram.com/legacy",
        "instagram_url": "https://instagram.com/preferred",
    }
    urls = social_urls_from_mapping(data)
    assert urls["instagram_url"] == "https://instagram.com/preferred"
