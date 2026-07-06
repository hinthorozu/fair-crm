"""FastAPI dependency injection for the Exhibitor Scraper module."""

from functools import lru_cache
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuthorizationAdapter
from app.integrations.kyrox_core.dev_bypass import (
    AllowAllAuthorizationAdapter,
    dev_bypass_enabled,
    resolve_auth_context,
)
from app.integrations.kyrox_core.ports import AuthorizationPort

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.scraper.read"
PERMISSION_CREATE = "fair_crm.scraper.create"
PERMISSION_UPDATE = "fair_crm.scraper.update"
PERMISSION_DELETE = "fair_crm.scraper.delete"
PERMISSION_RUN = "fair_crm.scraper.run"
PERMISSION_DOWNLOAD = "fair_crm.scraper.download"


def get_authorization_adapter() -> AuthorizationPort:
    if dev_bypass_enabled():
        return AllowAllAuthorizationAdapter()
    return HttpAuthorizationAdapter()


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


def _require_permission(permission_code: str):
    def dependency(
        auth: AuthContext = Depends(get_auth_context),
        authorization: AuthorizationPort = Depends(get_authorization_adapter),
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> AuthContext:
        if dev_bypass_enabled():
            return auth
        if credentials is None or not credentials.credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        if not authorization.check_permission(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            permission_code=permission_code,
            access_token=credentials.credentials,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return auth

    return dependency


require_read_permission = _require_permission(PERMISSION_READ)
require_create_permission = _require_permission(PERMISSION_CREATE)
require_update_permission = _require_permission(PERMISSION_UPDATE)
require_delete_permission = _require_permission(PERMISSION_DELETE)
require_run_permission = _require_permission(PERMISSION_RUN)
require_download_permission = _require_permission(PERMISSION_DOWNLOAD)
from app.modules.scraper.core.browser_service import BrowserConfig, BrowserService, create_browser_service
from app.modules.scraper.core.manifest_registry import ManifestRegistry, get_manifest_registry
from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.core.scraper_registry import ScraperAdapterRegistry, get_scraper_adapter_registry
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.services.scraper_dashboard_service import ScraperDashboardService
from app.modules.scraper.services.scraper_run_history_service import (
    ScraperRunHistoryService,
    create_run_history_service,
)
from app.modules.scraper.services.scraper_run_log_service import (
    ScraperRunLogService,
    create_run_log_service,
)
from app.modules.scraper.services.adapter_linked_fair_service import (
    AdapterLinkedFairService,
    create_adapter_linked_fair_service,
)
from app.modules.scraper.services.adapter_engine_service import (
    AdapterEngineService,
    create_adapter_engine_service,
)
from app.modules.scraper.services.scraper_adapter_service import (
    ScraperAdapterService,
    create_scraper_adapter_service,
)
from app.modules.scraper.services.scraper_service import ScraperService
from app.modules.scraper.infrastructure.repositories.scraper_adapter_repository import ScraperAdapterRepository
from app.modules.scraper.application.delete_adapter import DeleteAdapterUseCase
from app.modules.scraper.application.adapter_test_run_job_runner import (
    AdapterTestRunJobCommand,
    AdapterTestRunJobRunner,
)
from app.modules.scraper.application.enrichment_run_job_runner import EnrichmentRunJobRunner
from app.modules.scraper.application.run_adapter_test import (
    AdapterNotRegisteredError,
    RunAdapterTestCommand,
    RunAdapterTestUseCase,
)
from app.modules.scraper.application.run_enrichment import RunEnrichmentUseCase


@lru_cache
def get_company_normalizer() -> CompanyNormalizer:
    return CompanyNormalizer()


@lru_cache
def get_browser_config() -> BrowserConfig:
    return BrowserConfig.from_settings(get_settings())


def get_scraper_manager(
    registry: ScraperAdapterRegistry | None = None,
    normalizer: CompanyNormalizer | None = None,
    browser_service: BrowserService | None = None,
    manifest_registry: ManifestRegistry | None = None,
) -> ScraperManager:
    return ScraperManager(
        registry=registry or get_scraper_adapter_registry(),
        normalizer=normalizer or get_company_normalizer(),
        browser_service=browser_service,
        manifest_registry=manifest_registry or get_manifest_registry(),
    )


def get_default_scraper_manager() -> ScraperManager:
    return get_scraper_manager()


def get_scraper_run_history_service(db: Session = Depends(get_db)) -> ScraperRunHistoryService:
    return create_run_history_service(db)


def get_scraper_run_log_service(db: Session = Depends(get_db)) -> ScraperRunLogService:
    return create_run_log_service(db)


def get_adapter_linked_fair_service(db: Session = Depends(get_db)) -> AdapterLinkedFairService:
    return create_adapter_linked_fair_service(db)


def get_adapter_engine_service() -> AdapterEngineService:
    return create_adapter_engine_service()


def get_scraper_adapter_service(
    db: Session = Depends(get_db),
    manager: ScraperManager = Depends(get_default_scraper_manager),
) -> ScraperAdapterService:
    return create_scraper_adapter_service(ScraperAdapterRepository(db), manager)


def get_scraper_dashboard_service(
    manager: ScraperManager | None = None,
    run_history_service: ScraperRunHistoryService | None = None,
) -> ScraperDashboardService:
    return ScraperDashboardService(
        manager or get_default_scraper_manager(),
        run_history_service,
    )


def get_default_scraper_dashboard_service(
    manager: ScraperManager = Depends(get_default_scraper_manager),
    run_history_service: ScraperRunHistoryService = Depends(get_scraper_run_history_service),
) -> ScraperDashboardService:
    return get_scraper_dashboard_service(manager, run_history_service)


def get_scraper_service(
    manager: ScraperManager | None = None,
) -> ScraperService:
    return ScraperService(manager or get_scraper_manager())


_adapter_test_run_job_runner = AdapterTestRunJobRunner()


def get_adapter_test_run_job_runner() -> AdapterTestRunJobRunner:
    return _adapter_test_run_job_runner


def get_run_adapter_test_use_case(
    db: Session = Depends(get_db),
) -> RunAdapterTestUseCase:
    return RunAdapterTestUseCase(create_run_history_service(db), db)


_enrichment_run_job_runner = EnrichmentRunJobRunner()


def get_enrichment_run_job_runner() -> EnrichmentRunJobRunner:
    return _enrichment_run_job_runner


def get_run_enrichment_use_case(
    db: Session = Depends(get_db),
) -> RunEnrichmentUseCase:
    return RunEnrichmentUseCase(create_run_history_service(db), db)


def get_delete_adapter_use_case(
    db: Session = Depends(get_db),
    adapter_service: ScraperAdapterService = Depends(get_scraper_adapter_service),
) -> DeleteAdapterUseCase:
    return DeleteAdapterUseCase(db, adapter_service=adapter_service)
