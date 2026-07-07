"""Post-restore database health checks for maintenance restore jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

CRITICAL_TABLES: tuple[str, ...] = (
    "alembic_version",
    "crm_customers",
    "crm_fairs",
    "crm_contacts",
    "system_backups",
    "system_backup_restore_jobs",
)

COUNT_TABLES: tuple[str, ...] = (
    "crm_customers",
    "crm_fairs",
    "crm_contacts",
)


@dataclass(frozen=True)
class PostRestoreHealthResult:
    ok: bool
    migration_result: str
    customers_count: int | None = None
    fairs_count: int | None = None
    contacts_count: int | None = None
    error_message: str | None = None

    def summary_text(self) -> str:
        if not self.ok:
            return f"Post-restore health check failed: {self.error_message or 'unknown error'}"
        return (
            "Post-restore health check summary:\n"
            f"- migration: {self.migration_result}\n"
            f"- customers: {self.customers_count}\n"
            f"- fairs: {self.fairs_count}\n"
            f"- contacts: {self.contacts_count}"
        )

    def log_lines(self) -> list[str]:
        lines = ["Running post-restore health check"]
        if not self.ok:
            lines.append(f"Database connection: FAILED ({self.error_message})")
            lines.append(f"Migration result: {self.migration_result}")
            lines.append("Post-restore health check FAILED")
            return lines

        lines.append("Database connection: OK")
        lines.append(f"Migration result: {self.migration_result}")
        lines.append("Critical tables: OK")
        lines.append(f"customers count: {self.customers_count}")
        lines.append(f"fairs count: {self.fairs_count}")
        lines.append(f"contacts count: {self.contacts_count}")
        lines.append("Post-restore health check passed")
        return lines


def run_post_restore_health_check(
    *,
    database_url: str,
    migration_result: str = "success",
    engine_factory: Callable[..., Engine] | None = None,
) -> PostRestoreHealthResult:
    engine: Engine | None = None
    try:
        create = engine_factory or create_engine
        engine = create(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

            missing_tables: list[str] = []
            for table_name in CRITICAL_TABLES:
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
                    error_message=f"Missing critical tables: {', '.join(missing_tables)}",
                )

            counts: dict[str, int] = {}
            for table_name in COUNT_TABLES:
                counts[table_name] = int(
                    conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0
                )

        return PostRestoreHealthResult(
            ok=True,
            migration_result=migration_result,
            customers_count=counts["crm_customers"],
            fairs_count=counts["crm_fairs"],
            contacts_count=counts["crm_contacts"],
        )
    except Exception as exc:
        return PostRestoreHealthResult(
            ok=False,
            migration_result=migration_result,
            error_message=str(exc),
        )
    finally:
        if engine is not None:
            engine.dispose()
