"""Tests for shared import/scraper output field definitions."""

from app.shared.import_output_fields import (
    EXCEL_IMPORT_EXTRA_MAPPING_FIELDS,
    GRID_MAPPING_FIELDS,
    OUTPUT_KEY_TO_CANONICAL,
    STANDARD_IMPORT_MAPPING_FIELDS,
    WIZARD_MAPPING_FIELDS,
)


def test_standard_import_mapping_fields_include_social_urls():
    assert "instagram_url" in STANDARD_IMPORT_MAPPING_FIELDS
    assert "facebook_url" in STANDARD_IMPORT_MAPPING_FIELDS
    assert "linkedin_url" in STANDARD_IMPORT_MAPPING_FIELDS
    assert "youtube_url" in STANDARD_IMPORT_MAPPING_FIELDS
    assert "contact_first_name" not in STANDARD_IMPORT_MAPPING_FIELDS


def test_excel_import_extra_fields_are_not_scraper_output_fields():
    assert "contact_first_name" in EXCEL_IMPORT_EXTRA_MAPPING_FIELDS
    assert "contact_email" in EXCEL_IMPORT_EXTRA_MAPPING_FIELDS
    assert "contact_phone" in EXCEL_IMPORT_EXTRA_MAPPING_FIELDS
    assert "country" in EXCEL_IMPORT_EXTRA_MAPPING_FIELDS
    assert "city" in EXCEL_IMPORT_EXTRA_MAPPING_FIELDS
    assert "tax_number" in EXCEL_IMPORT_EXTRA_MAPPING_FIELDS


def test_output_key_to_canonical_maps_social_fields_to_url_keys():
    assert OUTPUT_KEY_TO_CANONICAL["instagram"] == "instagram_url"
    assert OUTPUT_KEY_TO_CANONICAL["facebook"] == "facebook_url"
    assert OUTPUT_KEY_TO_CANONICAL["linkedin"] == "linkedin_url"
    assert OUTPUT_KEY_TO_CANONICAL["youtube"] == "youtube_url"
    assert OUTPUT_KEY_TO_CANONICAL["customerName"] == "company_name"


def test_grid_mapping_fields_include_shared_and_excel_extra():
    assert STANDARD_IMPORT_MAPPING_FIELDS.issubset(GRID_MAPPING_FIELDS)
    assert EXCEL_IMPORT_EXTRA_MAPPING_FIELDS.issubset(GRID_MAPPING_FIELDS)
    assert GRID_MAPPING_FIELDS == STANDARD_IMPORT_MAPPING_FIELDS | EXCEL_IMPORT_EXTRA_MAPPING_FIELDS


def test_wizard_mapping_fields_accept_legacy_saved_mappings():
    assert "company_name" in WIZARD_MAPPING_FIELDS
    assert "contact_first_name" in WIZARD_MAPPING_FIELDS
    assert "contact_last_name" in WIZARD_MAPPING_FIELDS
    assert "instagram" in WIZARD_MAPPING_FIELDS
