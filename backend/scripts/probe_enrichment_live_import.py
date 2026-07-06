"""Live enrichment run with import batch + merge preview verification (dry_run=false)."""

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

from sqlalchemy import and_, exists, func, not_

from app.db.session import SessionLocal
from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.contacts.infrastructure.repositories.contact_repository import SqlAlchemyContactRepository
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
from app.modules.scraper.domain.enrichment_adapter import DEFAULT_ENRICHMENT_REQUESTED_FIELDS
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    ScraperRunHistoryRepository,
)
from app.modules.scraper.services.enrichment_candidate_service import list_enrichment_candidates
from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def _pick_organization_id(session) -> UUID:
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerWebsiteModel

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


def _build_merge_preview_builder(session) -> MergePreviewBuilder:
    customer_repo = SqlAlchemyCustomerRepository(session)
    return MergePreviewBuilder(
        customer_repository=customer_repo,
        communication_sync=CustomerCommunicationSyncService(SqlAlchemyCustomerCommunicationRepository(session)),
        participation_repository=SqlAlchemyParticipationRepository(session),
        contact_repository=SqlAlchemyContactRepository(session),
    )


def main() -> int:
    limit = 5
    requested_fields = list(DEFAULT_ENRICHMENT_REQUESTED_FIELDS)
    session = SessionLocal()
    try:
        organization_id = _pick_organization_id(session)
        candidates = list_enrichment_candidates(session, organization_id, limit=limit)
        if not candidates:
            print(json.dumps({"error": "No enrichment candidates"}, ensure_ascii=False))
            return 1

        customer_ids = [item.customer_id for item in candidates]
        emails_before = _email_counts(session, organization_id, customer_ids)

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

        runner = EnrichmentRunJobRunner()
        runner.run_enrichment(
            EnrichmentRunJobCommand(
                run_id=run.id,
                organization_id=organization_id,
                adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
                user_id=uuid4(),
                limit=limit,
                requested_fields=requested_fields,
                dry_run=False,
                max_pages=10,
            )
        )

        session.expire_all()
        completed = history_service.get_run(run.id)
        emails_after = _email_counts(session, organization_id, customer_ids)

        import_batch_id = completed.import_batch_id if completed else None
        batch = None
        import_rows = []
        if import_batch_id is not None:
            batch_repo = SqlAlchemyImportBatchRepository(session)
            row_repo = SqlAlchemyImportRowRepository(session)
            batch = batch_repo.get_by_id(organization_id, import_batch_id)
            import_rows = row_repo.list_by_batch(organization_id, import_batch_id)

        preview_builder = _build_merge_preview_builder(session)
        row_reports = []
        for import_row in import_rows:
            raw = import_row.raw_data_json or {}
            raw_meta = raw.get("raw") if isinstance(raw.get("raw"), dict) else {}
            normalized = import_row.normalized_data_json or {}
            merge_preview = None
            if batch is not None:
                merge_preview = preview_builder.build_for_row(organization_id, batch, import_row)
            row_reports.append(
                {
                    "row_number": import_row.row_number,
                    "customer_id": str(import_row.match_customer_id) if import_row.match_customer_id else None,
                    "external_id": normalized.get("external_id"),
                    "company_name": normalized.get("company_name"),
                    "website": normalized.get("website"),
                    "email": normalized.get("email"),
                    "source_url": raw_meta.get("source_url") or raw_meta.get("email_source_url"),
                    "email_source_url": raw_meta.get("email_source_url"),
                    "match_reason": import_row.match_reason,
                    "match_confidence": import_row.match_confidence,
                    "status": import_row.status.value if hasattr(import_row.status, "value") else str(import_row.status),
                    "suggested_action": (
                        import_row.suggested_action.value
                        if import_row.suggested_action and hasattr(import_row.suggested_action, "value")
                        else None
                    ),
                    "merge_preview_email": _extract_merge_field(merge_preview, "email"),
                }
            )

        handoff_rows = completed.total_rows if completed else 0
        sample_customers = row_reports[:2]

        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "run_id": str(run.id),
            "import_batch_id": str(import_batch_id) if import_batch_id else None,
            "handoff_rows": handoff_rows,
            "merge_preview_rows": len(import_rows),
            "import_batch_created": import_batch_id is not None,
            "crm_email_records_unchanged": emails_before == emails_after,
            "emails_before": emails_before,
            "emails_after": emails_after,
            "batch_status": batch.status.value if batch and hasattr(batch.status, "value") else None,
            "sample_customers": sample_customers,
            "all_rows": row_reports,
        }
        output_path = BACKEND_ROOT / "data" / "enrichment-live-import-report.json"
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(output_path))
        return 0
    finally:
        session.close()


def _extract_merge_field(merge_preview: dict | None, field: str) -> dict | None:
    if not merge_preview:
        return None
    for group in merge_preview.get("groups") or []:
        for item in group.get("fields") or []:
            if item.get("field_key") == field:
                return item
    return None


if __name__ == "__main__":
    raise SystemExit(main())
