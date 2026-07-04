"""FastAPI dependency injection for the Exhibitor Scraper module."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fairs.api.dependencies import get_auth_context
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
from app.modules.scraper.services.scraper_adapter_service import (
    ScraperAdapterService,
    create_scraper_adapter_service,
)
from app.modules.scraper.infrastructure.repositories.scraper_adapter_repository import ScraperAdapterRepository
from app.modules.scraper.application.adapter_test_run_job_runner import (
    AdapterTestRunJobCommand,
    AdapterTestRunJobRunner,
)
from app.modules.scraper.application.run_adapter_test import (
    AdapterNotRegisteredError,
    RunAdapterTestCommand,
    RunAdapterTestUseCase,
)


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
    return RunAdapterTestUseCase(create_run_history_service(db))
