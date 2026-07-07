"""Post-restore database health checks for maintenance restore jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.shared.database_backup.database_keys import DatabaseKey

FAIR_CRM_CRITICAL_TABLES: tuple[str, ...] = (
    "alembic_version",
    "crm_customers",
    "crm_fairs",
    "crm_contacts",
    "system_backups",
    "system_backup_restore_jobs",
)

FAIR_CRM_COUNT_TABLES: tuple[str, ...] = (
    "crm_customers",
    "crm_fairs",
    "crm_contacts",
)

KYROX_CORE_CRITICAL_TABLES: tuple[str, ...] = (
    "alembic_version",
    "identity_users",
    "identity_organizations",
    "identity_roles",
    "identity_permissions",
    "identity_memberships",
)

KYROX_CORE_COUNT_TABLES: tuple[str, ...] = (
    "identity_users",
    "identity_organizations",
    "identity_roles",
    "identity_permissions",
    "identity_memberships",
)


@dataclass(frozen=True)
class PostRestoreHealthResult:
    ok: bool
    migration_result: str
    database_key: str
    customers_count: int | None = None
    fairs_count: int | None = None
    contacts_count: int | None = None
    users_count: int | None = None
    organizations_count: int | None = None
    roles_count: int | None = None
    permissions_count: int | None = None
    memberships_count: int | None = None
    error_message: str | None = None

    def summary_text(self) -> str:
        if not self.ok:
            return f"Post-restore health check failed: {self.error_message or 'unknown error'}"
        if self.database_key == DatabaseKey.KYROX_CORE.value:
            return (
                "Post-restore health check summary:\n"
                f"- database: {self.database_key}\n"
                f"- migration: {self.migration_result}\n"
                f"- users: {self.users_count}\n"
                f"- organizations: {self.organizations_count}\n"
                f"- roles: {self.roles_count}\n"
                f"- permissions: {self.permissions_count}\n"
                f"- memberships: {self.memberships_count}"
            )
        return (
            "Post-restore health check summary:\n"
            f"- database: {self.database_key}\n"
            f"- migration: {self.migration_result}\n"
            f"- customers: {self.customers_count}\n"
            f"- fairs: {self.fairs_count}\n"
            f"- contacts: {self.contacts_count}"
        )

    def log_lines(self) -> list[str]:
        lines = [f"Running post-restore health check ({self.database_key})"]
        if not self.ok:
            lines.append(f"Database connection: FAILED ({self.error_message})")
            lines.append(f"Migration result: {self.migration_result}")
            lines.append("Post-restore health check FAILED")
            return lines

        lines.append("Database connection: OK")
        lines.append(f"Migration result: {self.migration_result}")
        lines.append("Critical tables: OK")
        if self.database_key == DatabaseKey.KYROX_CORE.value:
            lines.extend(
                [
                    f"users count: {self.users_count}",
                    f"organizations count: {self.organizations_count}",
                    f"roles count: {self.roles_count}",
                    f"permissions count: {self.permissions_count}",
                    f"memberships count: {self.memberships_count}",
                ]
            )
        else:
            lines.extend(
                [
                    f"customers count: {self.customers_count}",
                    f"fairs count: {self.fairs_count}",
                    f"contacts count: {self.contacts_count}",
                ]
            )
        lines.append("Post-restore health check passed")
        return lines


def _critical_tables(database_key: DatabaseKey) -> tuple[str, ...]:
    if database_key == DatabaseKey.KYROX_CORE:
        return KYROX_CORE_CRITICAL_TABLES
    return FAIR_CRM_CRITICAL_TABLES


def _count_tables(database_key: DatabaseKey) -> tuple[str, ...]:
    if database_key == DatabaseKey.KYROX_CORE:
        return KYROX_CORE_COUNT_TABLES
    return FAIR_CRM_COUNT_TABLES


def run_post_restore_health_check(
    *,
    database_url: str,
    database_key: DatabaseKey | str = DatabaseKey.FAIR_CRM,
    migration_result: str = "success",
    engine_factory: Callable[..., Engine] | None = None,
) -> PostRestoreHealthResult:
    key = DatabaseKey(database_key)
    engine: Engine | None = None
    try:
        create = engine_factory or create_engine
        engine = create(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

            missing_tables: list[str] = []
            for table_name in _critical_tables(key):
                exists = conn.execute(
                    text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = :table_name"
                        ")"
                    ),
                    {"table_name": table_name},
                ).scalar()
                if not exists:
                    missing_tables.append(table_name)

            if missing_tables:
                return PostRestoreHealthResult(
                    ok=False,
                    migration_result=migration_result,
                    database_key=key.value,
                    error_message=f"Missing critical tables: {', '.join(missing_tables)}",
                )

            counts: dict[str, int] = {}
            for table_name in _count_tables(key):
                counts[table_name] = int(
                    conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0
                )

        if key == DatabaseKey.KYROX_CORE:
            return PostRestoreHealthResult(
                ok=True,
                migration_result=migration_result,
                database_key=key.value,
                users_count=counts["identity_users"],
                organizations_count=counts["identity_organizations"],
                roles_count=counts["identity_roles"],
                permissions_count=counts["identity_permissions"],
                memberships_count=counts["identity_memberships"],
            )

        return PostRestoreHealthResult(
            ok=True,
            migration_result=migration_result,
            database_key=key.value,
            customers_count=counts["crm_customers"],
            fairs_count=counts["crm_fairs"],
            contacts_count=counts["crm_contacts"],
        )
    except Exception as exc:
        return PostRestoreHealthResult(
            ok=False,
            migration_result=migration_result,
            database_key=DatabaseKey(database_key).value,
            error_message=str(exc),
        )
    finally:
        if engine is not None:
            engine.dispose()
