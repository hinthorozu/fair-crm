"""Unit tests for source-agnostic import row pipeline helpers."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.imports.application.import_row_builder import (
    build_import_rows,
    validate_mapped_rows,
)
from app.modules.imports.domain.entities import ImportBatch
from app.modules.imports.domain.services.duplicate_detector import BATCH_DUPLICATE_REASON
from app.modules.imports.domain.services.row_normalizer import normalize_row_data
from app.modules.imports.domain.services.row_validator import validate_import_row
from app.modules.imports.domain.value_objects import ImportRowStatus, ImportSourceType


def test_normalize_sparse_row_empty_optionals_become_null():
    normalized = normalize_row_data({"company_name": "Acme", "email": "", "phone": "  "})
    assert normalized["company_name"] == "Acme"
    assert normalized["email"] is None
    assert normalized["phone"] is None


def test_validate_company_name_only_has_no_errors():
    normalized = normalize_row_data({"company_name": "Only Name Ltd"})
    assert validate_import_row(normalized) == []


def test_validate_rejects_empty_company_name():
    normalized = normalize_row_data({"company_name": ""})
    assert validate_import_row(normalized) == ["no_company_name"]


def test_validate_rejects_too_short_company_name():
    normalized = normalize_row_data({"company_name": "A"})
    assert validate_import_row(normalized) == ["invalid_company_name"]


def test_validate_does_not_check_email():
    normalized = normalize_row_data({"company_name": "Acme", "email": "not-an-email"})
    # Unsalvageable emails are dropped by the shared sanitize pipeline; row stays valid.
    assert normalized["email"] is None
    assert validate_import_row(normalized) == []


def test_normalize_row_data_uses_shared_email_sanitize_pipeline():
    normalized = normalize_row_data(
        {
            "company_name": "Acme",
            "email": "info [at] company [dot] com?subject=x",
            "contact_email": "sales(at)ornek.com><i class=",
        }
    )
    assert normalized["email"] == "info@company.com"
    assert normalized["contact_email"] == "sales@ornek.com"


def test_normalize_row_data_keeps_valid_multi_email_and_drops_junk_parts():
    normalized = normalize_row_data(
        {
            "company_name": "Acme",
            "email": "info@a.com; not-an-email; sales@a.com",
        }
    )
    assert normalized["email"] == "info@a.com;sales@a.com"


def test_validate_mapped_rows_detects_batch_duplicate():
    rows = validate_mapped_rows(
        [
            {"company_name": "Same Co Ltd"},
            {"company_name": "SAME CO LTD"},
        ]
    )
    assert rows[0].status == ImportRowStatus.VALID
    assert rows[1].status == ImportRowStatus.INVALID
    assert BATCH_DUPLICATE_REASON in rows[1].errors


def test_build_import_rows_marks_company_name_only_ready():
    org_id = uuid4()
    now = datetime.now(tz=UTC)
    batch = ImportBatch.create_from_canonical(
        organization_id=org_id,
        fair_id=None,
        source_type=ImportSourceType.EXCEL,
        file_name="test.xlsx",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        raw_preview_json={},
        now=now,
    )
    rows = build_import_rows(
        batch=batch,
        raw_rows=[{"company_name": "New Co"}],
        customers=[],
        fair_id=None,
        now=now,
    )
    assert len(rows) == 1
    assert rows[0].status == ImportRowStatus.READY_TO_CREATE
    assert rows[0].match_reason == "no_match"
    assert rows[0].validation_errors_json is None
