"""Mark stuck enrichment runs as failed (maintenance)."""
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app

create_app()

from sqlalchemy import text

from app.db.session import SessionLocal
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service

STUCK_RUN_IDS = [
    "4663211f-bcee-4d9c-97b3-764018ffa7ce",
    "d9676392-bdb2-4bd1-98e5-7e70816b9fe8",
    "37bdb433-5288-4d7a-8288-0d676b28389a",
]
REASON = (
    "Run islem sirasinda enrichment state tablosu eksik oldugu icin aday sorgusu basarisiz oldu. "
    "Migration 0042 uygulandiktan sonra yeni run baslatin."
)


def main() -> None:
    db = SessionLocal()
    try:
        history = create_run_history_service(db)
        for run_id in STUCK_RUN_IDS:
            row = db.execute(
                text("SELECT status FROM scraper_run_history WHERE id = :id"),
                {"id": run_id},
            ).fetchone()
            if row is None:
                print(f"skip missing {run_id}")
                continue
            if row[0] != "running":
                print(f"skip {run_id} status={row[0]}")
                continue
            history.fail_run(UUID(run_id), error_message=REASON, finished_at=datetime.now(UTC))
            print(f"failed {run_id}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
