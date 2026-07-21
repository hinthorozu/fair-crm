"""Customer contact enrichment state and single-customer run API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.customers.api.dependencies import require_read_permission
from app.modules.scraper.api.dependencies import (
    get_enrichment_run_job_runner,
    get_run_enrichment_use_case,
    require_run_permission,
)
from app.modules.scraper.api.schemas import (
    CustomerContactEnrichmentRunRequest,
    CustomerContactEnrichmentStateResponse,
    ScraperRunHistoryResponse,
)
from app.modules.scraper.application.enrichment_run_job_runner import (
    EnrichmentRunJobCommand,
    EnrichmentRunJobRunner,
)
from app.modules.scraper.application.run_enrichment import (
    RunEnrichmentCommand,
    RunEnrichmentUseCase,
)
from app.modules.scraper.services.scraper_run_history_service import create_run_history_service
from app.modules.scraper.services.scraper_run_log_service import create_run_log_service
from app.modules.scraper.services.single_customer_enrichment_service import (
    SingleCustomerEnrichmentError,
    get_customer_contact_enrichment_state,
    recent_run_logs_for_state,
    validate_single_customer_enrichment_run,
)
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from app.shared.background_jobs import run_blocking_background_task

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


@router.get(
    "/{customer_id}/contact-enrichment-state",
    response_model=CustomerContactEnrichmentStateResponse,
    summary="Müşteri iletişim zenginleştirme durumu",
)
def get_customer_contact_enrichment_state_endpoint(
    customer_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read_permission)],
    db: Annotated[Session, Depends(get_db)],
) -> CustomerContactEnrichmentStateResponse:
    history_service = create_run_history_service(db)
    try:
        view = get_customer_contact_enrichment_state(
            db,
            organization_id=auth.organization_id,
            customer_id=customer_id,
            run_history_service=history_service,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    log_service = create_run_log_service(db)
    logs = recent_run_logs_for_state(log_service, view.last_enrichment_run_id, limit=100)
    return CustomerContactEnrichmentStateResponse.from_view(view, recent_logs=logs)


@router.post(
    "/{customer_id}/contact-enrichment/run",
    response_model=ScraperRunHistoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Tek müşteri için iletişim zenginleştirme çalıştır",
)
def run_customer_contact_enrichment(
    customer_id: UUID,
    body: CustomerContactEnrichmentRunRequest,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(require_run_permission)],
    db: Annotated[Session, Depends(get_db)],
    use_case: Annotated[RunEnrichmentUseCase, Depends(get_run_enrichment_use_case)],
    job_runner: Annotated[EnrichmentRunJobRunner, Depends(get_enrichment_run_job_runner)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> ScraperRunHistoryResponse:
    history_service = create_run_history_service(db)
    try:
        validate_single_customer_enrichment_run(
            db,
            organization_id=auth.organization_id,
            customer_id=customer_id,
            run_history_service=history_service,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SingleCustomerEnrichmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    run = use_case.execute(
        RunEnrichmentCommand(
            organization_id=auth.organization_id,
            adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
            limit=1,
        )
    )
    db.commit()
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_enrichment,
        EnrichmentRunJobCommand(
            run_id=run.id,
            organization_id=auth.organization_id,
            adapter_key=run.adapter_key,
            user_id=auth.user_id,
            access_token=_access_token(credentials),
            limit=1,
            requested_fields=body.requested_fields,
            dry_run=body.dry_run,
            max_pages=body.max_pages or 10,
            customer_ids=[customer_id],
            # Card enrich always re-scans even when CRM email exists; duplicates
            # are stripped before handoff and merged without overwrite on apply.
            include_existing_email=True,
        ),
    )
    return ScraperRunHistoryResponse.from_entity(run)
