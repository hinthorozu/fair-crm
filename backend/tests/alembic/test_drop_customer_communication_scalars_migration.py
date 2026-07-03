"""Pre-check behavior for migration 0021_drop_customer_communication_scalars."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest

_migration_path = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0021_drop_customer_communication_scalars.py"
)
_spec = spec_from_file_location("migration_0021_drop_customer_communication_scalars", _migration_path)
assert _spec and _spec.loader
migration = module_from_spec(_spec)
_spec.loader.exec_module(migration)

_CUSTOMER_ID = UUID("00000000-0000-0000-0000-000000000001")


def _empty_mappings_result() -> MagicMock:
    result = MagicMock()
    result.mappings.return_value = []
    return result


def test_split_emails_dedupes_and_normalizes():
    assert migration._split_emails("Info@A.com; sales@a.com, INFO@a.com") == [
        "info@a.com",
        "sales@a.com",
    ]


def test_verify_backfill_passes_when_no_mismatches():
    connection = MagicMock()
    connection.execute.side_effect = [
        _empty_mappings_result(),
        _empty_mappings_result(),
        _empty_mappings_result(),
    ]

    migration._verify_backfill(connection)


def test_verify_backfill_fails_on_phone_mismatch():
    phone_rows = MagicMock()
    phone_rows.mappings.return_value = [{"id": _CUSTOMER_ID, "phone": "905551234567"}]
    child_phones = MagicMock()
    child_phones.scalars.return_value = []

    connection = MagicMock()
    connection.execute.side_effect = [phone_rows, child_phones]

    with pytest.raises(RuntimeError, match="Cannot drop crm_customers.phone"):
        migration._verify_backfill(connection)


def test_verify_backfill_fails_on_email_mismatch():
    email_rows = MagicMock()
    email_rows.mappings.return_value = [{"id": _CUSTOMER_ID, "email": "missing@example.com"}]
    child_emails = MagicMock()
    child_emails.scalars.return_value = []

    connection = MagicMock()
    connection.execute.side_effect = [
        _empty_mappings_result(),
        _empty_mappings_result(),
        email_rows,
        child_emails,
    ]

    with pytest.raises(RuntimeError, match="Cannot drop crm_customers.email"):
        migration._verify_backfill(connection)
