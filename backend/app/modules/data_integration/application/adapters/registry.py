"""Registry for Universal Source Adapters — new sources plug in without engine changes."""

from pathlib import PurePath

from app.modules.data_integration.application.adapters.excel_adapter import ExcelSourceAdapter
from app.modules.data_integration.domain.source_adapter import SourceAdapter
from app.modules.imports.domain.exceptions import InvalidImportFileError
from app.modules.imports.domain.value_objects import ImportSourceType


class SourceAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[ImportSourceType, SourceAdapter] = {}
        self._extension_map: dict[str, ImportSourceType] = {}

    def register(self, adapter: SourceAdapter, *, file_extensions: tuple[str, ...] = ()) -> None:
        self._adapters[adapter.source_type] = adapter
        for ext in file_extensions:
            self._extension_map[ext.lower()] = adapter.source_type

    def get(self, source_type: ImportSourceType) -> SourceAdapter:
        adapter = self._adapters.get(source_type)
        if adapter is None:
            raise InvalidImportFileError(f"No adapter registered for source type: {source_type}")
        return adapter

    def get_for_file(self, file_name: str) -> SourceAdapter:
        suffix = PurePath(file_name).suffix.lower()
        source_type = self._extension_map.get(suffix)
        if source_type is None:
            raise InvalidImportFileError(f"No adapter registered for file type: {suffix or file_name}")
        return self.get(source_type)

    def list_source_types(self) -> list[ImportSourceType]:
        return list(self._adapters.keys())


_default_registry: SourceAdapterRegistry | None = None


def get_source_adapter_registry() -> SourceAdapterRegistry:
    global _default_registry
    if _default_registry is None:
        registry = SourceAdapterRegistry()
        registry.register(ExcelSourceAdapter(), file_extensions=(".xlsx",))
        _default_registry = registry
    return _default_registry
