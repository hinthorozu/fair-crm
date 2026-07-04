"""Tests for canonical import schema validation."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.shared.canonical_import.schema import (
    CanonicalImportDocument,
    CanonicalImportMetadata,
    CanonicalImportRow,
    CanonicalImportSource,
    CanonicalImportSourceType,
)
from app.shared.canonical_import.validator import CanonicalImportValidationError, validate_canonical_import


def _sample_document(*, row_count: int = 1) -> CanonicalImportDocument:
    rows = [
        CanonicalImportRow(
            company_name="ABC LTD",
            normalized_company_name="abc ltd",
            website="https://abc.com",
            emails=["info@abc.com"],
            phones=["+902121112233"],
            country="Türkiye",
            city="İstanbul",
            hall="2",
            stand="A-12",
            raw={"category": "Gıda"},
        )
        for _ in range(row_count)
    ]
    return CanonicalImportDocument(
        source=CanonicalImportSource(
            type=CanonicalImportSourceType.SCRAPER,
            adapter_key="tuyap_new",
            fair_id=uuid4(),
            run_id=uuid4(),
            source_url="https://foodist.test/brands",
        ),
        metadata=CanonicalImportMetadata(
            created_at=datetime(2026, 7, 4, 12, 0, tzinfo=UTC),
            row_count=row_count,
        ),
        rows=rows,
    )


def test_validate_canonical_import_accepts_valid_document():
    document = _sample_document()
    validated = validate_canonical_import(document.model_dump(mode="json"))
    assert validated.source.type == CanonicalImportSourceType.SCRAPER
    assert validated.metadata.row_count == 1
    assert validated.rows[0].company_name == "ABC LTD"


def test_validate_canonical_import_rejects_row_count_mismatch():
    document = _sample_document()
    payload = document.model_dump(mode="json")
    payload["metadata"]["row_count"] = 99
    with pytest.raises(CanonicalImportValidationError):
        validate_canonical_import(payload)


def test_validate_canonical_import_rejects_scraper_without_adapter_key():
    document = _sample_document()
    payload = document.model_dump(mode="json")
    payload["source"]["adapter_key"] = None
    with pytest.raises(CanonicalImportValidationError):
        validate_canonical_import(payload)


def test_validate_canonical_import_rejects_unknown_top_level_fields():
    document = _sample_document()
    payload = document.model_dump(mode="json")
    payload["legacy_field"] = "keep-out"
    with pytest.raises(CanonicalImportValidationError):
        validate_canonical_import(payload)


def test_validate_canonical_import_rejects_empty_company_name():
    document = _sample_document()
    payload = document.model_dump(mode="json")
    payload["rows"][0]["company_name"] = ""
    with pytest.raises(CanonicalImportValidationError):
        validate_canonical_import(payload)
