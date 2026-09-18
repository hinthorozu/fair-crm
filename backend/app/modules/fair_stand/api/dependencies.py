from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.dashboard.api.dependencies import require_dashboard_access
from app.modules.fair_stand.application.get_catalog_bootstrap import GetCatalogBootstrapUseCase
from app.modules.fair_stand.application.get_item import GetItemUseCase
from app.modules.fair_stand.infrastructure.catalog_repository import SqlAlchemyFairStandCatalogRepository

require_fair_stand_catalog_access = require_dashboard_access


def get_catalog_repository(db: Session = Depends(get_db)) -> SqlAlchemyFairStandCatalogRepository:
    return SqlAlchemyFairStandCatalogRepository(db)


def get_catalog_bootstrap_use_case(
    repository: SqlAlchemyFairStandCatalogRepository = Depends(get_catalog_repository),
) -> GetCatalogBootstrapUseCase:
    return GetCatalogBootstrapUseCase(repository)


def get_item_use_case(
    repository: SqlAlchemyFairStandCatalogRepository = Depends(get_catalog_repository),
) -> GetItemUseCase:
    return GetItemUseCase(repository)
