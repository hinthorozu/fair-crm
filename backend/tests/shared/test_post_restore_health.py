"""Tests for post-restore health checks."""

from unittest.mock import MagicMock

import pytest

from app.shared.database_backup.post_restore_health import (
    PostRestoreHealthResult,
    run_post_restore_health_check,
)


def _mock_engine(*, connect_ok: bool = True, missing_tables: list[str] | None = None, counts: dict[str, int] | None = None, connect_error: Exception | None = None):
    missing_tables = missing_tables or []
    counts = counts or {"crm_customers": 3, "crm_fairs": 1, "crm_contacts": 2}

    class ConnectionContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement, params=None):
            result = MagicMock()
            if params and "table_name" in params:
                table_name = params["table_name"]
                result.scalar.return_value = table_name not in missing_tables
                return result
            sql = str(statement)
            if "SELECT 1" in sql:
                result.scalar.return_value = 1
                return result
            if "SELECT COUNT(*)" in sql:
                for table_name, count in counts.items():
                    if table_name in sql:
                        result.scalar.return_value = count
                        return result
                result.scalar.return_value = 0
                return result
            result.scalar.return_value = None
            return result

    engine = MagicMock()
    if connect_error is not None:
        engine.connect.side_effect = connect_error
    else:
        engine.connect.return_value = ConnectionContext()
    engine.dispose = MagicMock()
    return engine


def test_post_restore_health_check_success():
    engine = _mock_engine()
    result = run_post_restore_health_check(
        database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
        migration_result="success",
        engine_factory=lambda *args, **kwargs: engine,
    )

    assert result.ok is True
    assert result.database_key == "fair_crm"
    assert result.customers_count == 3
    assert result.fairs_count == 1
    assert result.contacts_count == 2
    assert "migration: success" in result.summary_text()
    assert any("Post-restore health check passed" in line for line in result.log_lines())


def test_post_restore_health_check_missing_table_fails():
    engine = _mock_engine(missing_tables=["crm_fairs"])
    result = run_post_restore_health_check(
        database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
        engine_factory=lambda *args, **kwargs: engine,
    )

    assert result.ok is False
    assert "crm_fairs" in (result.error_message or "")
    assert "failed" in result.summary_text().lower()


def test_post_restore_health_check_connection_error_fails():
    engine = _mock_engine(connect_error=RuntimeError("connection refused"))
    result = run_post_restore_health_check(
        database_url="postgresql://postgres:postgres@localhost:5432/fair_crm",
        engine_factory=lambda *args, **kwargs: engine,
    )

    assert result.ok is False
    assert "connection refused" in (result.error_message or "")


def test_post_restore_health_check_kyrox_core_success():
    counts = {
        "identity_users": 5,
        "identity_organizations": 2,
        "identity_roles": 3,
        "identity_permissions": 10,
        "identity_memberships": 7,
    }
    engine = _mock_engine(counts=counts)
    result = run_post_restore_health_check(
        database_url="postgresql://postgres:postgres@localhost:5432/kyrox_core",
        database_key="kyrox_core",
        migration_result="success",
        engine_factory=lambda *args, **kwargs: engine,
    )

    assert result.ok is True
    assert result.database_key == "kyrox_core"
    assert result.users_count == 5
    assert result.roles_count == 3
    assert "users: 5" in result.summary_text()
