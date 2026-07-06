"""Verify enrichment run end-to-end via live API."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app

create_app()

from app.db.session import SessionLocal
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates
from app.modules.scraper.services.enrichment_run_summary_loader import load_enrichment_summary_for_run
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.types.scraper_site import ScraperSiteKey

BASE_URL = "http://127.0.0.1:8001"
ORG_ID = "00000000-0000-4000-8000-000000000010"
HEADERS = {
    "Authorization": "Bearer dev-bypass",
    "X-Organization-Id": ORG_ID,
    "Content-Type": "application/json",
}
ADAPTER = ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT
POLL_INTERVAL_SEC = 2
POLL_TIMEOUT_SEC = 180


def main() -> None:
    db = SessionLocal()
    try:
        org_uuid = UUID(ORG_ID)
        candidates = list_enrichment_candidates(db, org_uuid, limit=5)
        print(f"candidate_count={len(candidates)}")
    finally:
        db.close()

    payload = {
        "limit": 5,
        "dry_run": True,
        "requested_fields": ["email", "phone"],
        "max_pages": 3,
    }
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        health = client.get("/health")
        health.raise_for_status()
        print(f"health={health.json()}")

        start = client.post(
            f"/api/v1/scraper/adapters/{ADAPTER}/enrichment-run",
            headers=HEADERS,
            json=payload,
        )
        start.raise_for_status()
        run = start.json()
        run_id = run["id"]
        print(f"started run_id={run_id} status={run['status']}")

        final = run
        deadline = time.time() + POLL_TIMEOUT_SEC
        while time.time() < deadline:
            if final.get("status") in {"completed", "failed", "cancelled"}:
                break
            time.sleep(POLL_INTERVAL_SEC)
            detail = client.get(f"/api/v1/scraper/runs/{run_id}", headers=HEADERS)
            detail.raise_for_status()
            final = detail.json()
            print(f"poll status={final['status']}")

        logs_resp = client.get(
            f"/api/v1/scraper/runs/{run_id}/logs",
            headers=HEADERS,
            params={"limit": 500},
        )
        logs_resp.raise_for_status()
        logs_payload = logs_resp.json()
        steps = [item["step"] for item in logs_payload.get("items", [])]

    db = SessionLocal()
    try:
        summary = load_enrichment_summary_for_run(create_run_log_service(db), UUID(run_id))
    finally:
        db.close()

    report = {
        "run_id": run_id,
        "status": final.get("status"),
        "duration_ms": final.get("duration_ms"),
        "finished_at": final.get("finished_at"),
        "error_message": final.get("error_message"),
        "import_batch_id": final.get("import_batch_id"),
        "enrichment_summary": summary or final.get("enrichment_summary"),
        "log_steps_in_order": steps,
        "expected_steps_present": {
            "started": "started" in steps,
            "candidates_query_started": "candidates_query_started" in steps,
            "candidates_query_finished": "candidates_query_finished" in steps,
            "candidates_loaded": "candidates_loaded" in steps,
            "website_fetch_started": "website_fetch_started" in steps,
            "website_fetch_success_or_failed": any(
                s in steps for s in ("website_fetch_success", "website_fetch_failed")
            ),
            "contact_extracted": "contact_extracted" in steps,
            "handoff_row_created_or_skipped": any(
                s in steps for s in ("handoff_row_created", "handoff_row_skipped")
            ),
            "dry_run_or_import_batch": any(
                s in steps for s in ("dry_run", "import_batch_created", "no_rows")
            ),
            "run_finished": "run_finished" in steps,
        },
        "stuck_running": final.get("status") == "running",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
