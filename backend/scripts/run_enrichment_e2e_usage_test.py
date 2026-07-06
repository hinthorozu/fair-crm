"""End-to-end customer contact enrichment usage test on live data."""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app

create_app()

from sqlalchemy import and_, exists, func, not_

from app.db.session import SessionLocal
from app.modules.activities.infrastructure.repositories.activity_repository import SqlAlchemyActivityRepository
from app.modules.contacts.infrastructure.repositories.contact_repository import SqlAlchemyContactRepository
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.imports.application.apply_import_decisions import (
    ApplyImportDecisionsCommand,
    ApplyImportDecisionsUseCase,
)
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.merge_preview_builder import MergePreviewBuilder
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.run_enrichment import RunEnrichmentCommand, RunEnrichmentUseCase
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.extractors.contact_extractor import is_junk_email
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates
from app.modules.scraper.services.enrichment_run_executor import execute_enrichment_run
from app.modules.scraper.services.customer_enrichment_state_service import load_state_map
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from tests.conftest import AllowAllAuthorization, NoOpAudit

ORG_ID = UUID("00000000-0000-4000-8000-000000000010")
USER_ID = UUID("00000000-0000-4000-8000-000000000001")
ACCESS_TOKEN = "dev-bypass"
REQUESTED_FIELDS = ["email", "phone", "address", "instagram", "facebook", "linkedin", "youtube"]
DRY_RUN_LIMIT = 20
LIVE_LIMIT = 15
ADORN_CUSTOMER_ID = UUID("8ef6a8dc-4ee5-58f5-ab2b-5564510a6233")
ADORN_EXPECTED_EMAIL = "info@fakibabatekstil.com"


def _pick_organization_id(session) -> UUID:
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


def _result_row(result) -> dict[str, Any]:
    first_email = result.emails[0] if result.emails else None
    first_phone = result.phones[0] if result.phones else None
    social = {
        key: (result.social_links.get(key).value if result.social_links.get(key) else None)
        for key in ("instagram", "facebook", "linkedin", "youtube")
    }
    has_social = any(social.values())
    email_value = first_email.value if first_email else None
    return {
        "customer_id": str(result.customer_id),
        "company_name": result.company_name,
        "website": result.website,
        "status": result.status,
        "email": email_value,
        "email_source_url": first_email.source_url if first_email else None,
        "email_is_placeholder": bool(email_value and is_junk_email(email_value)),
        "phone": first_phone.value if first_phone else None,
        "phone_source_url": first_phone.source_url if first_phone else None,
        "address": result.address.value if result.address else None,
        **social,
        "has_social": has_social,
        "error": result.error,
    }


def _summarize_results(results, *, run_id: str, duration_ms: int | None) -> dict[str, Any]:
    rows = [_result_row(item) for item in results]
    websites_fetched = sum(1 for item in rows if item["status"] in {"found", "not_found"})
    emails_found = sum(1 for item in results if item.emails)
    phones_found = sum(1 for item in results if item.phones)
    social_found = sum(1 for item in rows if item["has_social"])
    not_found = sum(1 for item in results if item.status == "not_found")
    failed = sum(1 for item in results if item.status == "failed")
    placeholders = [item for item in rows if item["email_is_placeholder"]]
    successful = [item for item in rows if item["email"] and not item["email_is_placeholder"]]
    not_found_rows = [item for item in rows if item["status"] == "not_found"]
    failed_rows = [item for item in rows if item["status"] == "failed"]

    adorn = next((item for item in rows if item["customer_id"] == str(ADORN_CUSTOMER_ID)), None)
    cloudflare_check = None
    if adorn is not None:
        cloudflare_check = {
            "customer_id": str(ADORN_CUSTOMER_ID),
            "company_name": adorn["company_name"],
            "website": adorn["website"],
            "email_found": adorn["email"],
            "expected_email": ADORN_EXPECTED_EMAIL,
            "cloudflare_email_captured": adorn["email"] == ADORN_EXPECTED_EMAIL,
            "phone": adorn["phone"],
        }

    return {
        "run_id": run_id,
        "customers_scanned": len(results),
        "candidate_count_available": None,
        "websites_fetched": websites_fetched,
        "emails_found": emails_found,
        "phones_found": phones_found,
        "social_found": social_found,
        "email_not_found": not_found,
        "failed": failed,
        "duration_ms": duration_ms,
        "placeholder_emails_captured": len(placeholders),
        "placeholder_examples": placeholders[:5],
        "cloudflare_adorn_check": cloudflare_check,
        "sample_success": successful[:5],
        "sample_not_found": not_found_rows[:5],
        "sample_failed": failed_rows[:5],
    }


def _run_enrichment(
    session,
    *,
    organization_id: UUID,
    limit: int,
    dry_run: bool,
) -> tuple[dict[str, Any], list]:
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
    started_at = time.time()
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
            user_id=USER_ID,
            access_token=ACCESS_TOKEN,
            limit=limit,
            requested_fields=REQUESTED_FIELDS,
            dry_run=dry_run,
            max_pages=10,
        )
    )
    session.expire_all()
    completed = history_service.get_run(run.id)
    duration_ms = completed.duration_ms if completed and completed.duration_ms else int((time.time() - started_at) * 1000)
    results = captured.get("results") or []
    summary = _summarize_results(results, run_id=str(run.id), duration_ms=duration_ms)
    summary["import_batch_id"] = str(completed.import_batch_id) if completed and completed.import_batch_id else None
    summary["run_status"] = completed.status.value if completed else None
    summary["handoff_rows"] = len(handoff.canonical_rows or []) if (handoff := captured.get("handoff")) else 0
    return summary, list(results)


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


def _build_apply_stack(session):
    comm_repo = SqlAlchemyCustomerCommunicationRepository(session)
    apply_use_case = ApplyImportUseCase(
        SqlAlchemyImportBatchRepository(session),
        SqlAlchemyImportRowRepository(session),
        SqlAlchemyCustomerRepository(session),
        CustomerCommunicationSyncService(comm_repo),
        SqlAlchemyContactRepository(session),
        SqlAlchemyActivityRepository(session),
        SqlAlchemyParticipationRepository(session),
        AllowAllAuthorization(),
        NoOpAudit(),
        session,
    )
    decisions_use_case = ApplyImportDecisionsUseCase(
        SqlAlchemyImportBatchRepository(session),
        SqlAlchemyImportRowRepository(session),
        apply_use_case,
        AllowAllAuthorization(),
        NoOpAudit(),
    )
    preview_builder = MergePreviewBuilder(
        customer_repository=SqlAlchemyCustomerRepository(session),
        communication_sync=CustomerCommunicationSyncService(comm_repo),
        participation_repository=SqlAlchemyParticipationRepository(session),
        contact_repository=SqlAlchemyContactRepository(session),
    )
    return apply_use_case, decisions_use_case, preview_builder


def _merge_preview_row(session, preview_builder, organization_id, batch, import_row) -> dict[str, Any]:
    normalized = import_row.normalized_data_json or {}
    raw = import_row.raw_data_json or {}
    raw_meta = raw.get("raw") if isinstance(raw.get("raw"), dict) else {}
    preview = preview_builder.build_for_row(organization_id, batch, import_row)
    return {
        "row_id": str(import_row.id),
        "row_number": import_row.row_number,
        "customer_id": str(import_row.match_customer_id) if import_row.match_customer_id else None,
        "external_id": normalized.get("external_id"),
        "company_name": normalized.get("company_name"),
        "email": normalized.get("email"),
        "phone": normalized.get("phone"),
        "source_url": raw_meta.get("source_url") or raw_meta.get("email_source_url"),
        "match_reason": import_row.match_reason,
        "status": import_row.status.value if hasattr(import_row.status, "value") else str(import_row.status),
        "merge_preview_email_outcome": _extract_merge_field(preview, "email"),
    }


def _extract_merge_field(merge_preview: dict | None, field: str) -> dict | None:
    if not merge_preview:
        return None
    for group in merge_preview.get("groups") or []:
        for item in group.get("fields") or []:
            if item.get("field_key") == field:
                return item
    return None


def _pick_reliable_rows(import_rows) -> list:
    reliable = []
    for row in import_rows:
        normalized = row.normalized_data_json or {}
        email = normalized.get("email")
        if not email or is_junk_email(str(email)):
            continue
        if row.match_customer_id is None:
            continue
        reliable.append(row)
        if len(reliable) >= 3:
            break
    return reliable


def _state_snapshot(session, organization_id: UUID, customer_id: UUID) -> dict[str, Any] | None:
    state_map = load_state_map(session, organization_id, [customer_id])
    state = state_map.get(customer_id)
    if state is None:
        return None
    return {
        "status": state.last_email_scan_status,
        "last_email_found": state.last_email_found,
        "last_source_url": state.last_source_url,
    }


def main() -> int:
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "organization_id": str(ORG_ID),
        "dry_run_limit": DRY_RUN_LIMIT,
        "live_limit": LIVE_LIMIT,
    }
    session = SessionLocal()
    try:
        organization_id = _pick_organization_id(session)
        candidates_before_dry = list_enrichment_candidates(session, organization_id, limit=DRY_RUN_LIMIT)
        report["candidates_before_dry_run"] = len(candidates_before_dry)

        print(f"[1/4] Dry run limit={DRY_RUN_LIMIT} ...")
        dry_summary, dry_results = _run_enrichment(
            session,
            organization_id=organization_id,
            limit=DRY_RUN_LIMIT,
            dry_run=True,
        )
        dry_summary["candidate_count_available"] = len(candidates_before_dry)
        report["dry_run"] = dry_summary

        candidates_before_live = list_enrichment_candidates(session, organization_id, limit=LIVE_LIMIT)
        report["candidates_before_live_import"] = len(candidates_before_live)
        live_customer_ids = [item.customer_id for item in candidates_before_live]
        emails_before_live = _email_counts(session, organization_id, live_customer_ids)

        print(f"[2/4] Live import limit={LIVE_LIMIT} ...")
        live_summary, _live_results = _run_enrichment(
            session,
            organization_id=organization_id,
            limit=LIVE_LIMIT,
            dry_run=False,
        )
        live_summary["candidate_count_available"] = len(candidates_before_live)
        report["live_import"] = live_summary

        import_batch_id = live_summary.get("import_batch_id")
        batch_repo = SqlAlchemyImportBatchRepository(session)
        row_repo = SqlAlchemyImportRowRepository(session)
        _, decisions_use_case, preview_builder = _build_apply_stack(session)

        merge_preview_rows: list[dict[str, Any]] = []
        import_rows = []
        batch = None
        if import_batch_id:
            batch = batch_repo.get_by_id(organization_id, UUID(import_batch_id))
            import_rows = row_repo.list_by_batch(organization_id, UUID(import_batch_id))
            if batch is not None:
                merge_preview_rows = [
                    _merge_preview_row(session, preview_builder, organization_id, batch, row)
                    for row in import_rows
                ]

        emails_after_live = _email_counts(session, organization_id, live_customer_ids)
        report["live_import"]["merge_preview"] = {
            "import_batch_id": import_batch_id,
            "import_batch_created": import_batch_id is not None,
            "merge_preview_row_count": len(import_rows),
            "crm_email_records_unchanged": emails_before_live == emails_after_live,
            "emails_before": emails_before_live,
            "emails_after": emails_after_live,
            "batch_status": batch.status.value if batch and hasattr(batch.status, "value") else None,
            "rows": merge_preview_rows,
        }

        reliable_rows = _pick_reliable_rows(import_rows)
        report["apply"] = {"selected_rows": [], "results": [], "state_transitions": {}}

        if reliable_rows and batch is not None:
            print(f"[3/4] Apply {len(reliable_rows)} reliable rows ...")
            pending_states = {
                str(row.match_customer_id): _state_snapshot(session, organization_id, row.match_customer_id)
                for row in reliable_rows
                if row.match_customer_id
            }
            apply_result = decisions_use_case.execute(
                ApplyImportDecisionsCommand(
                    organization_id=organization_id,
                    user_id=USER_ID,
                    access_token=ACCESS_TOKEN,
                    batch_id=batch.id,
                    row_ids=[row.id for row in reliable_rows],
                )
            )
            session.commit()
            session.expire_all()

            applied_details = []
            for row in reliable_rows:
                customer_id = row.match_customer_id
                if customer_id is None:
                    continue
                normalized = row.normalized_data_json or {}
                comm = CustomerCommunicationSyncService(
                    SqlAlchemyCustomerCommunicationRepository(session)
                ).load_for_customer(customer_id)
                state_after = _state_snapshot(session, organization_id, customer_id)
                applied_details.append(
                    {
                        "customer_id": str(customer_id),
                        "company_name": normalized.get("company_name"),
                        "expected_email": normalized.get("email"),
                        "crm_emails": [item.email for item in comm.emails],
                        "crm_phones": [item.phone for item in comm.phones],
                        "state_before_apply": pending_states.get(str(customer_id)),
                        "state_after_apply": state_after,
                    }
                )

            report["apply"]["selected_rows"] = merge_preview_rows[: len(reliable_rows)]
            report["apply"]["results"] = {
                "processed_count": apply_result.processed_count,
                "failed_count": apply_result.failed_count,
                "not_processed_count": apply_result.not_processed_count,
                "errors": [
                    {"row_id": str(item.row_id), "row_number": item.row_number, "message": item.message}
                    for item in apply_result.errors
                ],
                "applied_customers": applied_details,
            }

            print("[4/4] State transition checks after apply ...")
            state_checks: dict[str, Any] = {}
            if applied_details:
                target = applied_details[0]
                customer_id = UUID(target["customer_id"])
                comm_sync = CustomerCommunicationSyncService(
                    SqlAlchemyCustomerCommunicationRepository(session)
                )
                now = datetime.now(tz=UTC)

                state_checks["after_apply"] = target["state_after_apply"]
                state_checks["pending_merge_to_email_found"] = (
                    target["state_before_apply"] is not None
                    and target["state_before_apply"]["status"] == CustomerEnrichmentScanStatus.PENDING_MERGE
                    and target["state_after_apply"] is not None
                    and target["state_after_apply"]["status"] == CustomerEnrichmentScanStatus.EMAIL_FOUND
                )

                comm_sync.sync_from_value_lists(
                    organization_id=organization_id,
                    customer_id=customer_id,
                    now=now,
                    emails=[],
                    sync_email=True,
                )
                session.commit()
                state_checks["after_delete_last_email"] = _state_snapshot(session, organization_id, customer_id)
                state_checks["state_reset_when_no_email"] = state_checks["after_delete_last_email"] is None
                phone_count = (
                    session.query(CustomerPhoneModel)
                    .filter(CustomerPhoneModel.customer_id == customer_id)
                    .count()
                )
                state_checks["crm_phone_preserved_after_email_delete"] = phone_count > 0

                comm_sync.sync_from_value_lists(
                    organization_id=organization_id,
                    customer_id=customer_id,
                    now=now,
                    emails=["keep-a@test.local", "keep-b@test.local"],
                    sync_email=True,
                )
                _seed_enrichment_state(session, organization_id, customer_id)
                session.commit()
                comm_sync.sync_from_value_lists(
                    organization_id=organization_id,
                    customer_id=customer_id,
                    now=now,
                    emails=["keep-a@test.local"],
                    sync_email=True,
                )
                session.commit()
                preserved = _state_snapshot(session, organization_id, customer_id)
                state_checks["after_delete_one_of_two_emails"] = preserved
                state_checks["state_preserved_when_email_remains"] = (
                    preserved is not None
                    and preserved["status"] == CustomerEnrichmentScanStatus.EMAIL_FOUND
                )

            report["apply"]["state_transitions"] = state_checks
        else:
            report["apply"]["skipped_reason"] = "No reliable import rows to apply"

        output_path = BACKEND_ROOT / "data" / "enrichment-e2e-usage-report.json"
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0
    finally:
        session.close()


def _seed_enrichment_state(session, organization_id: UUID, customer_id: UUID) -> None:
    now = datetime.now(tz=UTC)
    existing = (
        session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id == customer_id,
        )
        .one_or_none()
    )
    if existing is not None:
        session.delete(existing)
        session.flush()
    session.add(
        CustomerEnrichmentStateModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            website="https://state-test.local",
            last_enrichment_run_id=None,
            last_email_scan_at=now,
            last_email_scan_status=CustomerEnrichmentScanStatus.EMAIL_FOUND,
            last_email_found="keep-a@test.local",
            last_source_url="https://state-test.local",
            last_error=None,
            retry_after=None,
            created_at=now,
            updated_at=now,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
