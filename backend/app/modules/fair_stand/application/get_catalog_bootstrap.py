from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps

from app.modules.fair_stand.application.item_mapper import CatalogCategory, CatalogPreview, ItemAggregate
from app.modules.fair_stand.infrastructure.catalog_repository import SqlAlchemyFairStandCatalogRepository


@dataclass(frozen=True)
class CatalogBootstrap:
    revision: str
    categories: list[CatalogCategory]
    items: list[ItemAggregate]
    preview_kinds: list[CatalogPreview]


class GetCatalogBootstrapUseCase:
    def __init__(self, repository: SqlAlchemyFairStandCatalogRepository) -> None:
        self._repository = repository

    def execute(self) -> CatalogBootstrap:
        categories = self._repository.list_active_categories()
        items = self._repository.list_items(active_only=True)
        preview_kinds = self._repository.list_preview_payloads(active_only=False)
        digest = sha256(
            dumps(
                {
                    "categories": [category.__dict__ for category in categories],
                    "items": [item.payload for item in items],
                    "previewKinds": [preview.__dict__ for preview in preview_kinds],
                },
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return CatalogBootstrap(
            revision=digest,
            categories=categories,
            items=items,
            preview_kinds=preview_kinds,
        )
