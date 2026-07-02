"""Source adapters — one implementation per external data origin."""

from app.modules.data_integration.application.adapters.excel_adapter import ExcelSourceAdapter
from app.modules.data_integration.application.adapters.registry import (
    SourceAdapterRegistry,
    get_source_adapter_registry,
)

__all__ = [
    "ExcelSourceAdapter",
    "SourceAdapterRegistry",
    "get_source_adapter_registry",
]
