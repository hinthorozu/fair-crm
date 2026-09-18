from __future__ import annotations

from app.modules.fair_stand.application.item_mapper import ItemAggregate
from app.modules.fair_stand.infrastructure.catalog_repository import SqlAlchemyFairStandCatalogRepository


class GetItemUseCase:
    def __init__(self, repository: SqlAlchemyFairStandCatalogRepository) -> None:
        self._repository = repository

    def execute(self, item_key: str) -> ItemAggregate | None:
        return self._repository.get_item(item_key, active_only=True)
