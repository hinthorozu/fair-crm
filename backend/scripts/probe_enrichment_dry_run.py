"""Live customer contact enrichment dry_run probe (real HTTP, no mock fetcher)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app

create_app()

from sqlalchemy import func

from app.db.session import SessionLocal
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.run_enrichment import RunEnrichmentCommand, RunEnrichmentUseCase
from app.modules.scraper.domain.enrichment_adapter import DEFAULT_ENRICHMENT_REQUESTED_FIELDS
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates
from app.modules.scraper.services.enrichment_run_executor import execute_enrichment_run
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _pick_organization_id(session) -> UUID:
    from sqlalchemy import and_, exists, not_

    from app.modules.customers.infrastructure.persistence.models import CustomerModel

    has_email = exists().where(
        and_(
            CustomerEmailModel.customer_id == CustomerModel.id,
            CustomerEmailModel.organization_id == CustomerModel.organization_id,
        )
    )
    row = (
        session.query(CustomerWebsiteModel.organization_id, func.count(CustomerModel.id))
        .join(CustomerModel, CustomerModel.id == CustomerWebsiteModel.customer_id)
        .filter(
            CustomerModel.deleted_at.is_(None),
            CustomerWebsiteModel.website.isnot(None),
            CustomerWebsiteModel.website != "",
            not_(has_email),
        )
        .group_by(CustomerWebsiteModel.organization_id)
        .order_by(func.count(CustomerModel.id).desc())
        .first()
    )
    if row is None:
        raise RuntimeError("No organization with enrichment candidates found")
    return row[0]


def _email_counts(session, organization_id: UUID, customer_ids: list[UUID]) -> dict[str, int]:
    if not customer_ids:
        return {}
    rows = (
        session.query(CustomerEmailModel.customer_id, func.count(CustomerEmailModel.id))
        .filter(
            CustomerEmailModel.organization_id == organization_id,
            CustomerEmailModel.customer_id.in_(customer_ids),
        )
        .group_by(CustomerEmailModel.customer_id)
        .all()
    )
    counts = {str(customer_id): 0 for customer_id in customer_ids}
    for customer_id, count in rows:
        counts[str(customer_id)] = int(count)
    return counts


def main() -> int:
    limit = 10
    requested_fields = ["email", "phone", "address", "instagram", "facebook", "linkedin", "youtube"]
    session = SessionLocal()
    try:
        organization_id = _pick_organization_id(session)
        candidates = list_enrichment_candidates(session, organization_id, limit=limit)
        if not candidates:
            print(json.dumps({"error": "No enrichment candidates"}, ensure_ascii=False))
            return 1

        customer_ids = [item.customer_id for item in candidates]
        emails_before = _email_counts(session, organization_id, customer_ids)

        captured: dict[str, object] = {}

        def live_executor(db, org_id, **kwargs):
            execution = execute_enrichment_run(db, org_id, **kwargs)
            results, handoff = execution.results, execution.handoff
            captured["results"] = results
            captured["handoff"] = handoff
            return results, handoff

        history_repo = ScraperRunHistoryRepository(session)
        history_service = ScraperRunHistoryService(history_repo)
        use_case = RunEnrichmentUseCase(history_service, session)
        run = use_case.execute(
            RunEnrichmentCommand(
                organization_id=organization_id,
                adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
                limit=limit,
            )
        )
        session.commit()

        runner = EnrichmentRunJobRunner(executor=live_executor)
        runner.run_enrichment(
            EnrichmentRunJobCommand(
                run_id=run.id,
                organization_id=organization_id,
                adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
                user_id=uuid4(),
                limit=limit,
                requested_fields=requested_fields,
                dry_run=True,
                max_pages=10,
            )
        )

        session.expire_all()
        completed = history_service.get_run(run.id)
        log_service = create_run_log_service(session)
        logs = log_service.list_logs(run.id, limit=500)
        emails_after = _email_counts(session, organization_id, customer_ids)

        results = captured.get("results") or []
        handoff = captured.get("handoff") or ScraperImportHandoff()

        handoff_json_rows: list[dict[str, object]] = []
        handoff_json_path = completed.output_json_path if completed else None
        if handoff_json_path:
            handoff_payload = json.loads(Path(handoff_json_path).read_text(encoding="utf-8"))
            handoff_json_rows = handoff_payload.get("rows") or []

        rows = []
        for result in results:
            first_email = result.emails[0] if result.emails else None
            first_phone = result.phones[0] if result.phones else None
            rows.append(
                {
                    "customer_id": str(result.customer_id),
                    "company_name": result.company_name,
                    "website": result.website,
                    "status": result.status,
                    "email": first_email.value if first_email else None,
                    "email_source_url": first_email.source_url if first_email else None,
                    "phone": first_phone.value if first_phone else None,
                    "phone_source_url": first_phone.source_url if first_phone else None,
                    "address": result.address.value if result.address else None,
                    "address_source_url": result.address.source_url if result.address else None,
                    "instagram": (
                        result.social_links.get("instagram").value
                        if result.social_links.get("instagram")
                        else None
                    ),
                    "facebook": (
                        result.social_links.get("facebook").value
                        if result.social_links.get("facebook")
                        else None
                    ),
                    "linkedin": (
                        result.social_links.get("linkedin").value
                        if result.social_links.get("linkedin")
                        else None
                    ),
                    "youtube": (
                        result.social_links.get("youtube").value
                        if result.social_links.get("youtube")
                        else None
                    ),
                    "error": result.error,
                }
            )

        crm_unchanged = emails_before == emails_after
        customer_event_steps = {
            "candidate_selected",
            "website_fetch_started",
            "website_fetch_success",
            "website_fetch_failed",
            "contact_extracted",
            "email_found",
            "not_found",
            "handoff_row_created",
            "handoff_row_skipped",
        }
        log_items = [
            {
                "step": item.step,
                "level": item.level.value if hasattr(item.level, "value") else str(item.level),
                "message": item.message,
                "metadata": item.metadata,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in logs
        ]
        customer_logs: dict[str, list[dict[str, object]]] = {}
        for item in log_items:
            if item["step"] not in customer_event_steps:
                continue
            customer_id = (item.get("metadata") or {}).get("customer_id")
            if not customer_id:
                continue
            customer_logs.setdefault(str(customer_id), []).append(item)

        websites_fetched_pages = sum(1 for item in log_items if item["step"] == "website_fetch_success")

        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "organization_id": str(organization_id),
            "run_id": str(run.id),
            "dry_run": True,
            "candidate_count_available": len(candidates),
            "customers": rows,
            "summary": {
                "customers_scanned": len(results),
                "websites_fetched_pages": websites_fetched_pages,
                "emails_found": sum(1 for item in results if item.emails),
                "not_found": sum(1 for item in results if item.status == "not_found"),
                "failed": sum(1 for item in results if item.status == "failed"),
                "found": sum(1 for item in results if item.status == "found"),
                "import_batch_id": str(completed.import_batch_id) if completed and completed.import_batch_id else None,
                "import_batch_created": completed.import_batch_id is not None if completed else False,
                "handoff_rows": len(handoff.canonical_rows or []),
                "run_status": completed.status.value if completed else None,
            },
            "merge_preview": {
                "crm_email_records_unchanged": crm_unchanged,
                "emails_before": emails_before,
                "emails_after": emails_after,
                "handoff_json_path": handoff_json_path,
                "handoff_row_metadata_external_ids": [
                    meta.get("external_id") for meta in (handoff.row_metadata or [])
                ],
                "handoff_json_external_ids": [row.get("external_id") for row in handoff_json_rows],
                "handoff_json_customer_ids_in_raw": [
                    (row.get("raw") or {}).get("customer_id") for row in handoff_json_rows
                ],
            },
            "customer_logs": customer_logs,
            "logs": log_items,
        }
        output_path = BACKEND_ROOT / "data" / "enrichment-dry-run-report.json"
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
