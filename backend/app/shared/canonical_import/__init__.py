"""Canonical import schema — source-agnostic contract for Import Engine."""

from app.shared.canonical_import.schema import (
    CanonicalImportDocument,
    CanonicalImportMetadata,
    CanonicalImportRow,
    CanonicalImportSource,
    CanonicalImportSourceType,
)
from app.shared.canonical_import.scraper_mapper import scraper_handoff_to_canonical
from app.shared.canonical_import.validator import CanonicalImportValidationError, validate_canonical_import

__all__ = [
    "CanonicalImportDocument",
    "CanonicalImportMetadata",
    "CanonicalImportRow",
    "CanonicalImportSource",
    "CanonicalImportSourceType",
    "CanonicalImportValidationError",
    "scraper_handoff_to_canonical",
    "validate_canonical_import",
]
