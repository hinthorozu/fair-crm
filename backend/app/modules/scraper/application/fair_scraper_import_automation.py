"""Create and analyze import batches after fair scraper automation runs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.integrations.kyrox_core.dev_bypass import AllowAllAuthorizationAdapter, NoOpAuditAdapter, dev_bypass_enabled
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.imports.application.analyze_canonical_import import AnalyzeCanonicalImportUseCase
from app.modules.imports.application.canonical_batch_mapper import (
    build_import_batch_from_canonical,
    build_import_rows_from_canonical,
)
from app.modules.imports.domain.exceptions import InvalidCanonicalImportError
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.modules.scraper.domain.enrichment_adapter import is_customer_contact_enrichment_adapter
from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import serialize_handoff_to_canonical_json
from app.shared.canonical_import.validator import CanonicalImportValidationError, validate_canonical_import
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository


def create_and_analyze_import_batch_from_handoff(
    db: Session,
    *,
    organization_id: UUID,
    fair_id: UUID | None,
    run_id: UUID,
    handoff: ScraperImportHandoff,
    adapter_key: str,
    source_url: str,
    user_id: UUID,
    access_token: str = "",
) -> UUID:
    """Persist canonical scraper handoff as import batch and run CRM matching."""
    is_enrichment = is_customer_contact_enrichment_adapter(adapter_key)
    if fair_id is not None:
        fair = SqlAlchemyFairRepository(db).get_by_id(organization_id, fair_id)
        if fair is None:
            raise InvalidCanonicalImportError("Fair not found for import automation")
    elif not is_enrichment:
        raise InvalidCanonicalImportError("fair_id is required for scraper import automation")

    document_dict = serialize_handoff_to_canonical_json(
        handoff,
        adapter_key=adapter_key,
        run_id=run_id,
        fair_id=fair_id,
        source_url=source_url,
    )
    try:
        validated = validate_canonical_import(document_dict)
    except CanonicalImportValidationError as exc:
        raise InvalidCanonicalImportError(str(exc)) from exc

    now = datetime.now(tz=UTC)
    batch_repo = SqlAlchemyImportBatchRepository(db)
    row_repo = SqlAlchemyImportRowRepository(db)

    batch = build_import_batch_from_canonical(
        validated,
        organization_id=organization_id,
        fair_id=fair_id,
        now=now,
    )
    saved_batch = batch_repo.add(batch)
    rows = build_import_rows_from_canonical(
        validated,
        batch_id=saved_batch.id,
        organization_id=organization_id,
        now=now,
    )
    if rows:
        row_repo.add_many(rows)

    authorization = AllowAllAuthorizationAdapter()
    audit: HttpAuditAdapter | NoOpAuditAdapter = (
        NoOpAuditAdapter() if dev_bypass_enabled() else HttpAuditAdapter()
    )
    analyze_use_case = AnalyzeCanonicalImportUseCase(
        batch_repo,
        row_repo,
        SqlAlchemyCustomerRepository(db),
        SqlAlchemyParticipationRepository(db),
        authorization,
        audit,
    )
    analyze_use_case.execute(
        organization_id=organization_id,
        batch_id=saved_batch.id,
        user_id=user_id,
        access_token=access_token,
        skip_permission_check=True,
    )
    return saved_batch.id
