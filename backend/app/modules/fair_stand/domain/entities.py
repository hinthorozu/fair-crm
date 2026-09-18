from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogCategory:
    catalog_key: str
    catalog_name: str
    catalog_index: int


@dataclass(frozen=True)
class ItemAggregate:
    payload: dict
