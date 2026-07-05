"""Shared import/scraper output field definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportOutputFieldDefinition:
    output_key: str
    canonical_key: str
    label_tr: str
    required: bool = False


IMPORT_OUTPUT_FIELD_DEFINITIONS: tuple[ImportOutputFieldDefinition, ...] = (
    ImportOutputFieldDefinition("customerName", "company_name", "Firma Adı", required=True),
    ImportOutputFieldDefinition("phone", "phone", "Telefon"),
    ImportOutputFieldDefinition("email", "email", "E-posta"),
    ImportOutputFieldDefinition("address", "address", "Adres"),
    ImportOutputFieldDefinition("website", "website", "Website"),
    ImportOutputFieldDefinition("hall", "hall", "Salon / Hall"),
    ImportOutputFieldDefinition("stand", "stand", "Stand"),
    ImportOutputFieldDefinition("instagram", "instagram_url", "Instagram"),
    ImportOutputFieldDefinition("facebook", "facebook_url", "Facebook"),
    ImportOutputFieldDefinition("linkedin", "linkedin_url", "LinkedIn"),
    ImportOutputFieldDefinition("youtube", "youtube_url", "YouTube"),
    ImportOutputFieldDefinition("notes", "notes", "Not"),
)

# Excel Import-only fields (not scraper output fields).
EXCEL_IMPORT_EXTRA_FIELD_DEFINITIONS: tuple[ImportOutputFieldDefinition, ...] = (
    ImportOutputFieldDefinition("contact_first_name", "contact_first_name", "Yetkili Adı"),
    ImportOutputFieldDefinition("contact_email", "contact_email", "Yetkili E-posta"),
    ImportOutputFieldDefinition("contact_phone", "contact_phone", "Yetkili Telefon"),
    ImportOutputFieldDefinition("country", "country", "Ülke"),
    ImportOutputFieldDefinition("city", "city", "Şehir"),
    ImportOutputFieldDefinition("tax_number", "tax_number", "Vergi No"),
)

OUTPUT_KEY_TO_CANONICAL: dict[str, str] = {
    definition.output_key: definition.canonical_key for definition in IMPORT_OUTPUT_FIELD_DEFINITIONS
}

CANONICAL_TO_OUTPUT_KEY: dict[str, str] = {
    definition.canonical_key: definition.output_key for definition in IMPORT_OUTPUT_FIELD_DEFINITIONS
}

STANDARD_IMPORT_MAPPING_FIELDS: frozenset[str] = frozenset(
    definition.canonical_key for definition in IMPORT_OUTPUT_FIELD_DEFINITIONS
)

EXCEL_IMPORT_EXTRA_MAPPING_FIELDS: frozenset[str] = frozenset(
    definition.canonical_key for definition in EXCEL_IMPORT_EXTRA_FIELD_DEFINITIONS
)

# Legacy Excel mapping keys still accepted for saved batches (not offered in UI).
LEGACY_IMPORT_MAPPING_FIELDS: frozenset[str] = frozenset(
    {
        "mobile_phone",
        "contact_last_name",
        "contact_title",
        "contact_department",
        "contact_mobile_phone",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
    }
)

WIZARD_MAPPING_FIELDS: frozenset[str] = (
    STANDARD_IMPORT_MAPPING_FIELDS | EXCEL_IMPORT_EXTRA_MAPPING_FIELDS | LEGACY_IMPORT_MAPPING_FIELDS
)

GRID_MAPPING_FIELDS: frozenset[str] = STANDARD_IMPORT_MAPPING_FIELDS | EXCEL_IMPORT_EXTRA_MAPPING_FIELDS

REQUIRED_IMPORT_MAPPING_FIELDS: frozenset[str] = frozenset(
    definition.canonical_key for definition in IMPORT_OUTPUT_FIELD_DEFINITIONS if definition.required
)

IMPORT_FIELD_LABELS_TR: dict[str, str] = {
    definition.canonical_key: definition.label_tr
    for definition in (*IMPORT_OUTPUT_FIELD_DEFINITIONS, *EXCEL_IMPORT_EXTRA_FIELD_DEFINITIONS)
}
