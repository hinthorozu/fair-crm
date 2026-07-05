"""Tests for Excel import row normalization with social URLs."""

from app.modules.imports.domain.services.header_mapping import map_header_to_field
from app.modules.imports.domain.services.row_normalizer import normalize_row_data


def test_map_header_to_field_maps_instagram_to_instagram_url():
    assert map_header_to_field("Instagram") == "instagram_url"
    assert map_header_to_field("Stand No") == "stand"
    assert map_header_to_field("Not") == "notes"


def test_normalize_row_data_includes_social_urls_from_short_keys():
    normalized = normalize_row_data(
        {
            "company_name": "Social Co",
            "instagram": "instagram.com/socialco",
            "linkedin_url": "https://linkedin.com/company/socialco",
        }
    )
    assert normalized["instagram_url"] == "https://instagram.com/socialco"
    assert normalized["linkedin_url"] == "https://linkedin.com/company/socialco"


def test_normalize_row_data_includes_social_urls_from_canonical_mapping_keys():
    normalized = normalize_row_data(
        {
            "company_name": "Social Co",
            "instagram_url": "https://instagram.com/socialco",
            "facebook_url": "https://facebook.com/socialco",
        }
    )
    assert normalized["instagram_url"] == "https://instagram.com/socialco"
    assert normalized["facebook_url"] == "https://facebook.com/socialco"
