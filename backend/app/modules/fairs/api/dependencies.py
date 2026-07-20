from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuditAdapter, HttpAuthorizationAdapter
from app.integrations.kyrox_core.dev_bypass import (
    AllowAllAuthorizationAdapter,
    NoOpAuditAdapter,
    dev_bypass_enabled,
    resolve_auth_context,
)
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.application.archive_fair import ArchiveFairUseCase
from app.modules.fairs.application.create_fair import CreateFairUseCase
from app.modules.fairs.application.get_fair import GetFairUseCase
from app.modules.fairs.application.list_fairs import ListFairsUseCase
from app.modules.fairs.application.restore_fair import RestoreFairUseCase
from app.modules.fairs.application.run_fair_enrichment import RunFairEnrichmentUseCase
from app.modules.fairs.application.run_fair_scraper import RunFairScraperUseCase
from app.modules.fairs.application.update_fair import UpdateFairUseCase
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.scraper.application.fair_scraper_job_runner import FairScraperJobRunner
from app.modules.scraper.application.enrichment_run_job_runner import EnrichmentRunJobRunner
from app.modules.scraper.services.scraper_run_history_service import (
    ScraperRunHistoryService,
    create_run_history_service,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.fairs.read"
PERMISSION_SCRAPER_RUN = "fair_crm.scraper.run"


def get_fair_repository(db: Session = Depends(get_db)) -> SqlAlchemyFairRepository:
    return SqlAlchemyFairRepository(db)


def get_authorization_adapter() -> AuthorizationPort:
    if dev_bypass_enabled():
        return AllowAllAuthorizationAdapter()
    return HttpAuthorizationAdapter()


def get_audit_adapter() -> HttpAuditAdapter | NoOpAuditAdapter:
    if dev_bypass_enabled():
        return NoOpAuditAdapter()
    return HttpAuditAdapter()


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    organization_id: UUID = Header(..., alias="X-Organization-Id"),
    dev_user_id: UUID | None = Header(default=None, alias="X-Dev-User-Id"),
) -> AuthContext:
    try:
        return resolve_auth_context(credentials, organization_id, dev_user_id=dev_user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc


def require_read_permission(
    auth: AuthContext = Depends(get_auth_context),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_READ,
        access_token=credentials.credentials,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return auth


def require_scraper_run_permission(
    auth: AuthContext = Depends(get_auth_context),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_SCRAPER_RUN,
        access_token=credentials.credentials,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return auth


def get_create_fair_use_case(
    repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateFairUseCase:
    return CreateFairUseCase(repository, authorization, audit)


def get_get_fair_use_case(
    repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
) -> GetFairUseCase:
    return GetFairUseCase(repository)


def get_list_fairs_use_case(
    repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
) -> ListFairsUseCase:
    return ListFairsUseCase(repository)


def get_update_fair_use_case(
    repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateFairUseCase:
    return UpdateFairUseCase(repository, authorization, audit)


def get_archive_fair_use_case(
    repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> ArchiveFairUseCase:
    return ArchiveFairUseCase(repository, authorization, audit)


def get_restore_fair_use_case(
    repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> RestoreFairUseCase:
    return RestoreFairUseCase(repository, authorization, audit)


def get_scraper_run_history_service(db: Session = Depends(get_db)) -> ScraperRunHistoryService:
    return create_run_history_service(db)


_fair_scraper_job_runner = FairScraperJobRunner()
_enrichment_run_job_runner = EnrichmentRunJobRunner()


def get_fair_scraper_job_runner() -> FairScraperJobRunner:
    return _fair_scraper_job_runner


def get_enrichment_run_job_runner() -> EnrichmentRunJobRunner:
    return _enrichment_run_job_runner


def get_run_fair_scraper_use_case(
    repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    run_history_service: ScraperRunHistoryService = Depends(get_scraper_run_history_service),
) -> RunFairScraperUseCase:
    return RunFairScraperUseCase(repository, run_history_service)


def get_run_fair_enrichment_use_case(
    repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    run_history_service: ScraperRunHistoryService = Depends(get_scraper_run_history_service),
    db: Session = Depends(get_db),
) -> RunFairEnrichmentUseCase:
    return RunFairEnrichmentUseCase(repository, run_history_service, db)
