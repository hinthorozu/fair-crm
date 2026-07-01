"""Unit tests for source-agnostic import row pipeline helpers."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.imports.application.import_row_builder import build_import_rows
from app.modules.imports.domain.entities import ImportBatch
from app.modules.imports.domain.services.row_normalizer import normalize_row_data
from app.modules.imports.domain.services.row_validator import validate_import_row
from app.modules.imports.domain.value_objects import ImportRowStatus


def test_normalize_sparse_row_empty_optionals_become_null():
    normalized = normalize_row_data({"company_name": "Acme", "email": "", "phone": "  "})
    assert normalized["company_name"] == "Acme"
    assert normalized["email"] is None
    assert normalized["phone"] is None


def test_validate_company_name_only_has_no_errors():
    normalized = normalize_row_data({"company_name": "Only Name Ltd"})
    assert validate_import_row(normalized) == []


def test_build_import_rows_marks_company_name_only_ready():
    org_id = uuid4()
    now = datetime.now(tz=UTC)
    batch = ImportBatch.create(
        organization_id=org_id,
        file_name="test.xlsx",
        total_rows=1,
        now=now,
    )
    rows = build_import_rows(
        batch=batch,
        raw_rows=[{"company_name": "New Co"}],
        customers=[],
        now=now,
    )
    assert len(rows) == 1
    assert rows[0].status == ImportRowStatus.READY_TO_CREATE
    assert rows[0].validation_errors_json is None
