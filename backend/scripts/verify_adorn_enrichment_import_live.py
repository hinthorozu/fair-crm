"""Live import batch enrichment for ADORN (dry_run=false)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app

create_app()

from app.db.session import SessionLocal
from app.modules.customers.infrastructure.persistence.communication_models import CustomerWebsiteModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.run_enrichment import RunEnrichmentCommand, RunEnrichmentUseCase
from app.modules.scraper.infrastructure.handoff_storage import resolve_handoff_path
from app.modules.scraper.services.customer_enrichment_state_service import reset_enrichment_states
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.types.scraper_site import ScraperSiteKey

ORG_ID = UUID("00000000-0000-4000-8000-000000000010")
USER_ID = UUID("00000000-0000-4000-8000-000000000001")
COMPANY = "ADORN"
EXPECTED_EMAIL = "info@fakibabatekstil.com"
EXPECTED_EMAIL_SOURCE = "https://fakibabatekstil.com/"
EXPECTED_PHONE = "+902243637878"


def _handoff_rows(run_id: UUID) -> list[dict]:
    path = resolve_handoff_path(run_id)
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("rows") or payload.get("canonical_rows") or []


def _find_adorn_row(rows: list[dict]) -> dict | None:
    for row in rows:
        name = str(row.get("company_name") or "")
        emails = row.get("emails") or []
        email_single = row.get("email")
        if COMPANY.lower() in name.lower():
            return row
        if any(EXPECTED_EMAIL in str(e) for e in emails):
            return row
        if email_single == EXPECTED_EMAIL:
            return row
    return None


def main() -> int:
    db = SessionLocal()
    try:
        customer = (
            db.query(CustomerModel)
            .filter(
                CustomerModel.organization_id == ORG_ID,
                CustomerModel.display_name.ilike(COMPANY),
            )
            .one()
        )
        reset_enrichment_states(db, organization_id=ORG_ID, customer_ids=[customer.id])
        db.commit()

        candidates = list_enrichment_candidates(db, ORG_ID, limit=5)
        if customer.id not in {c.customer_id for c in candidates}:
            print(json.dumps({"error": "ADORN not in top 5 candidates"}, ensure_ascii=False))
            return 1

        history = create_run_history_service(db)
        use_case = RunEnrichmentUseCase(history, db)
        run = use_case.execute(
            RunEnrichmentCommand(
                organization_id=ORG_ID,
                adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
                limit=5,
            )
        )
        db.commit()
        run_id = run.id
    finally:
        db.close()

    runner = EnrichmentRunJobRunner()
    runner.run_enrichment(
        EnrichmentRunJobCommand(
            run_id=run_id,
            organization_id=ORG_ID,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            user_id=USER_ID,
            limit=5,
            requested_fields=["email", "phone"],
            dry_run=False,
            max_pages=3,
        )
    )

    db = SessionLocal()
    try:
        completed = create_run_history_service(db).get_run(run_id)
    finally:
        db.close()

    rows = _handoff_rows(run_id)
    adorn = _find_adorn_row(rows)
    raw = (adorn or {}).get("raw") or {}
    emails = adorn.get("emails") if adorn else None
    phones = adorn.get("phones") if adorn else None
    email = emails[0] if isinstance(emails, list) and emails else adorn.get("email") if adorn else None
    phone = phones[0] if isinstance(phones, list) and phones else adorn.get("phone") if adorn else None

    report = {
        "run_id": str(run_id),
        "status": completed.status.value if completed else None,
        "duration_ms": completed.duration_ms if completed else None,
        "dry_run": False,
        "import_batch_id": str(completed.import_batch_id) if completed and completed.import_batch_id else None,
        "error_message": completed.error_message if completed else None,
        "adorn_row": adorn,
        "checks": {
            "completed": (completed.status.value if completed else None) == "completed",
            "import_batch_created": completed.import_batch_id is not None if completed else False,
            "adorn_row_found": adorn is not None,
            "email_matches": email == EXPECTED_EMAIL,
            "email_source_matches": str(raw.get("email_source_url") or "").rstrip("/")
            == EXPECTED_EMAIL_SOURCE.rstrip("/"),
            "phone_matches": phone == EXPECTED_PHONE,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))

    checks = report["checks"]
    ok = all(
        [
            checks["completed"],
            checks["import_batch_created"],
            checks["adorn_row_found"],
            checks["email_matches"],
            checks["email_source_matches"],
            checks["phone_matches"],
        ]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
