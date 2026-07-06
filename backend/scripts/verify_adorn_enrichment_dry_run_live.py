"""Live dry_run enrichment for ADORN via job runner (real HTTP)."""
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
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.run_enrichment import RunEnrichmentCommand, RunEnrichmentUseCase
from app.modules.scraper.infrastructure.handoff_storage import resolve_handoff_path
from app.modules.scraper.services.customer_enrichment_state_service import (
    is_customer_scan_eligible,
    load_state_map,
    reset_enrichment_states,
)
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.types.scraper_site import ScraperSiteKey

ORG_ID = UUID("00000000-0000-4000-8000-000000000010")
USER_ID = UUID("00000000-0000-4000-8000-000000000001")
COMPANY = "ADORN"
EXPECTED_EMAIL = "info@fakibabatekstil.com"
EXPECTED_EMAIL_SOURCE = "https://fakibabatekstil.com/"
EXPECTED_PHONE = "+902243637878"


def _find_adorn(session):
    row = (
        session.query(CustomerModel, CustomerWebsiteModel)
        .join(CustomerWebsiteModel, CustomerWebsiteModel.customer_id == CustomerModel.id)
        .filter(
            CustomerModel.organization_id == ORG_ID,
            CustomerModel.deleted_at.is_(None),
            CustomerModel.display_name.ilike(COMPANY),
        )
        .first()
    )
    if row is None:
        raise RuntimeError(f"{COMPANY} not found")
    return row[0], row[1]


def main() -> int:
    db = SessionLocal()
    try:
        customer, website_row = _find_adorn(db)
        state_map = load_state_map(db, ORG_ID, [customer.id])
        state = state_map.get(customer.id)
        if not is_customer_scan_eligible(state, website=website_row.website or ""):
            reset_enrichment_states(db, organization_id=ORG_ID, customer_ids=[customer.id])
            db.commit()

        candidates = list_enrichment_candidates(db, ORG_ID, limit=5)
        if customer.id not in {c.customer_id for c in candidates}:
            print(json.dumps({"error": "ADORN not in top 5 candidates after reset"}, ensure_ascii=False))
            return 1

        history = create_run_history_service(db)
        use_case = __import__(
            "app.modules.scraper.application.run_enrichment",
            fromlist=["RunEnrichmentUseCase"],
        ).RunEnrichmentUseCase(history, db)
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
            dry_run=True,
            max_pages=3,
        )
    )

    db = SessionLocal()
    try:
        completed = create_run_history_service(db).get_run(run_id)
    finally:
        db.close()

    handoff_path = resolve_handoff_path(run_id)
    handoff = json.loads(handoff_path.read_text(encoding="utf-8")) if handoff_path.is_file() else {}
    rows = handoff.get("canonical_rows") or []
    metadata_rows = handoff.get("row_metadata") or []

    adorn_row = None
    adorn_meta = None
    for index, row in enumerate(rows):
        name = str(row.get("company_name") or "")
        site = str(row.get("website") or "")
        if COMPANY.lower() in name.lower() or "fakibabatekstil" in site.lower():
            adorn_row = row
            adorn_meta = metadata_rows[index] if index < len(metadata_rows) else {}
            break

    report = {
        "run_id": str(run_id),
        "status": completed.status.value if completed else None,
        "duration_ms": completed.duration_ms if completed else None,
        "dry_run": True,
        "adorn_handoff_row": adorn_row,
        "adorn_metadata": adorn_meta,
        "checks": {},
    }

    if adorn_row and adorn_meta:
        email = str(adorn_row.get("email") or "")
        phone = str(adorn_row.get("phone") or "")
        email_source = str(adorn_meta.get("email_source_url") or "")
        phone_source = str(adorn_meta.get("phone_source_url") or "")
        report["checks"] = {
            "adorn_row_found": True,
            "email": email,
            "email_matches": email.lower() == EXPECTED_EMAIL,
            "email_source_url": email_source,
            "email_source_matches": email_source.rstrip("/") + "/"
            == EXPECTED_EMAIL_SOURCE.rstrip("/") + "/",
            "phone": phone,
            "phone_matches": phone == EXPECTED_PHONE,
            "phone_source_url": phone_source,
        }
    else:
        report["checks"] = {"adorn_row_found": False}

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    checks = report["checks"]
    ok = (
        report["status"] == "completed"
        and checks.get("adorn_row_found")
        and checks.get("email_matches")
        and checks.get("phone_matches")
        and checks.get("email_source_matches")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
