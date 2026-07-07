"""Maintenance CLI for executing persisted restore jobs outside the API lifecycle."""

from __future__ import annotations

import argparse
import os
import sys

from app.integrations.kyrox_core.dev_bypass import NoOpAuditAdapter
from app.modules.system_admin.application.restore_job_service import (
    RestoreJobMaintenanceCommand,
    RestoreJobMaintenanceRunner,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a persisted Fair CRM restore job")
    parser.add_argument("--job-id", required=True, help="Restore job UUID")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("TARGET_DATABASE_URL", ""),
        help="Target PostgreSQL URL (defaults to TARGET_DATABASE_URL env)",
    )
    parser.add_argument(
        "--allow-restore",
        action="store_true",
        default=os.environ.get("ALLOW_RESTORE", "").lower() in {"1", "true", "yes"},
        help="Required guard for destructive restore (or ALLOW_RESTORE=true)",
    )
    args = parser.parse_args(argv)

    from uuid import UUID

    try:
        job_id = UUID(args.job_id)
    except ValueError:
        print(f"Invalid job id: {args.job_id}", file=sys.stderr)
        return 1

    runner = RestoreJobMaintenanceRunner(audit=NoOpAuditAdapter())
    return runner.run(
        RestoreJobMaintenanceCommand(
            job_id=job_id,
            target_database_url=args.database_url,
            allow_restore=args.allow_restore,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
