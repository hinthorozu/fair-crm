"""Pre-check behavior for migration 0021_drop_customer_communication_scalars."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock

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


def test_split_emails_dedupes_and_normalizes():
    assert migration._split_emails("Info@A.com; sales@a.com, INFO@a.com") == [
        "info@a.com",
        "sales@a.com",
    ]


def test_verify_backfill_passes_when_no_mismatches():
    connection = MagicMock()
    connection.execute.side_effect = [
        MagicMock(scalar_one=MagicMock(return_value=0)),
        MagicMock(scalar_one=MagicMock(return_value=0)),
        MagicMock(mappings=MagicMock(return_value=[])),
    ]

    migration._verify_backfill(connection)


def test_verify_backfill_fails_on_phone_mismatch():
    connection = MagicMock()
    connection.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=2))

    with pytest.raises(RuntimeError, match="Cannot drop crm_customers.phone"):
        migration._verify_backfill(connection)


def test_verify_backfill_fails_on_email_mismatch():
    customer_id = "00000000-0000-0000-0000-000000000001"

    phone_result = MagicMock(scalar_one=MagicMock(return_value=0))
    website_result = MagicMock(scalar_one=MagicMock(return_value=0))
    email_rows = MagicMock(
        mappings=MagicMock(
            return_value=[{"id": customer_id, "email": "missing@example.com"}],
        ),
    )
    child_emails = MagicMock(scalars=MagicMock(return_value=[]))

    connection = MagicMock()
    connection.execute.side_effect = [phone_result, website_result, email_rows, child_emails]

    with pytest.raises(RuntimeError, match="Cannot drop crm_customers.email"):
        migration._verify_backfill(connection)
