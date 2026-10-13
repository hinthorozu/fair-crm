"""Systemd invokes this entry point only at the scheduled weekly time."""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.session import SessionLocal
from app.modules.fairs.application.tobb_sync_job_runner import TobbSyncJobRunner
from app.modules.fairs.infrastructure.tobb_run_repository import SqlAlchemyTobbRunRepository


def weekly_years(now: datetime) -> list[int]:
    local = now.astimezone(ZoneInfo("Europe/Istanbul"))
    return [local.year, local.year + 1]


def main() -> None:
    with SessionLocal() as session:
        run, created = SqlAlchemyTobbRunRepository(session).start(
            weekly_years(datetime.now(ZoneInfo("Europe/Istanbul"))), requested_by=None, automatic=True,
        )
        run_id = run.id
    if created:
        TobbSyncJobRunner().run(run_id)


if __name__ == "__main__":
    main()
