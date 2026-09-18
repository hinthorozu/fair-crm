from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from app.modules.fair_stand.application.item_mapper import CatalogCategory, ItemAggregate
from app.modules.fair_stand.infrastructure.catalog_repository import SqlAlchemyFairStandCatalogRepository


@dataclass(frozen=True)
class CatalogBootstrap:
    revision: str
    categories: list[CatalogCategory]
    items: list[ItemAggregate]


class GetCatalogBootstrapUseCase:
    def __init__(self, repository: SqlAlchemyFairStandCatalogRepository) -> None:
        self._repository = repository

    def execute(self) -> CatalogBootstrap:
        categories = self._repository.list_active_categories()
        items = self._repository.list_items(active_only=True)
        digest = sha256(
            dumps(
                {
                    "categories": [category.__dict__ for category in categories],
                    "items": [item.payload for item in items],
                },
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return CatalogBootstrap(revision=digest, categories=categories, items=items)
