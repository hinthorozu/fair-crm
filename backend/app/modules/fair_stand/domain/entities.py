from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogCategory:
    id: int
    catalog_name: str
    catalog_index: int


@dataclass(frozen=True)
class CatalogPreview:
    id: int
    display_name: str
    markup: str
    css_code: str
    sort_index: int
    is_active: bool


@dataclass(frozen=True)
class ItemAggregate:
    payload: dict
