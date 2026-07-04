"""CRUD and merge logic for managed scraper adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.domain.scraper_adapter import ScraperAdapter, normalize_adapter_key
from app.modules.scraper.domain.scraper_adapter_exceptions import (
    AdapterNotFoundError,
    DuplicateAdapterKeyError,
)
from app.modules.scraper.infrastructure.repositories.scraper_adapter_repository import (
    ScraperAdapterRepository,
)
from app.modules.scraper.manifests.scraper_manifest import ScraperManifest, ScraperStatus
from app.modules.scraper.services.scraper_dashboard_service import (
    build_adapter_features,
    resolve_actions_available,
)


@dataclass(frozen=True)
class ManagedAdapterView:
    id: UUID | None
    adapter_key: str
    display_name: str
    description: str | None
    status: str
    version: str
    features: list[dict[str, str | bool]]
    last_verified: str | None
    actions_available: list[str]
    is_active: bool
    manifest: dict[str, Any] | None
    last_verified_at: datetime | None
    is_registered: bool
    created_at: datetime | None
    updated_at: datetime | None


class ScraperAdapterService:
    def __init__(
        self,
        repository: ScraperAdapterRepository,
        manager: ScraperManager,
    ) -> None:
        self._repository = repository
        self._manager = manager

    def list_adapters(self, organization_id: UUID) -> list[ManagedAdapterView]:
        db_by_key = {
            record.adapter_key: record for record in self._repository.list_by_organization(organization_id)
        }
        results: list[ManagedAdapterView] = []
        seen: set[str] = set()

        for manifest in self._manager.list_manifests():
            record = db_by_key.get(manifest.adapter_key)
            results.append(self._merge_view(manifest, record))
            seen.add(manifest.adapter_key)

        for key, record in db_by_key.items():
            if key not in seen:
                results.append(self._view_from_record(record, manifest=None))

        return results

    def get_adapter(self, organization_id: UUID, adapter_key: str) -> ManagedAdapterView:
        normalized_key = normalize_adapter_key(adapter_key)
        record = self._repository.get_by_key(organization_id, normalized_key)
        manifest = self._try_get_manifest(normalized_key)
        if record is None and manifest is None:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")
        return self._merge_view(manifest, record) if manifest is not None else self._view_from_record(record)

    def create_adapter(
        self,
        organization_id: UUID,
        *,
        adapter_key: str,
        name: str,
        description: str | None = None,
        status: ScraperStatus = ScraperStatus.EXPERIMENTAL,
        version: str | None = None,
        manifest: dict[str, Any] | None = None,
        is_active: bool = True,
    ) -> ManagedAdapterView:
        normalized_key = normalize_adapter_key(adapter_key)
        if self._repository.get_by_key(organization_id, normalized_key, include_deleted=True) is not None:
            raise DuplicateAdapterKeyError(f"Adapter key already exists for organization: {normalized_key}")

        now = datetime.now(tz=UTC)
        adapter = ScraperAdapter.create(
            organization_id=organization_id,
            adapter_key=normalized_key,
            name=name,
            description=description,
            status=status,
            version=version,
            manifest=manifest,
            is_active=is_active,
            now=now,
        )
        saved = self._repository.add(adapter)
        registry_manifest = self._try_get_manifest(saved.adapter_key)
        return self._merge_view(registry_manifest, saved) if registry_manifest else self._view_from_record(saved)

    def update_adapter(
        self,
        organization_id: UUID,
        adapter_key: str,
        *,
        name: str | None = None,
        description: str | None = None,
        status: ScraperStatus | None = None,
        version: str | None = None,
        manifest: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> ManagedAdapterView:
        normalized_key = normalize_adapter_key(adapter_key)
        record = self._get_or_create_overlay(organization_id, normalized_key)
        now = datetime.now(tz=UTC)
        record.update_fields(
            name=name,
            description=description,
            status=status,
            version=version,
            manifest=manifest,
            is_active=is_active,
            now=now,
        )
        saved = self._repository.update(record)
        registry_manifest = self._try_get_manifest(saved.adapter_key)
        return self._merge_view(registry_manifest, saved) if registry_manifest else self._view_from_record(saved)

    def activate_adapter(self, organization_id: UUID, adapter_key: str) -> ManagedAdapterView:
        record = self._get_or_create_overlay(organization_id, normalize_adapter_key(adapter_key))
        record.activate(now=datetime.now(tz=UTC))
        saved = self._repository.update(record)
        registry_manifest = self._try_get_manifest(saved.adapter_key)
        return self._merge_view(registry_manifest, saved) if registry_manifest else self._view_from_record(saved)

    def deactivate_adapter(self, organization_id: UUID, adapter_key: str) -> ManagedAdapterView:
        record = self._get_or_create_overlay(organization_id, normalize_adapter_key(adapter_key))
        record.deactivate(now=datetime.now(tz=UTC))
        saved = self._repository.update(record)
        registry_manifest = self._try_get_manifest(saved.adapter_key)
        return self._merge_view(registry_manifest, saved) if registry_manifest else self._view_from_record(saved)

    def soft_delete_adapter(self, organization_id: UUID, adapter_key: str) -> None:
        normalized_key = normalize_adapter_key(adapter_key)
        record = self._repository.get_by_key(organization_id, normalized_key)
        if record is None:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")
        record.soft_delete(now=datetime.now(tz=UTC))
        self._repository.update(record)

    def _get_or_create_overlay(self, organization_id: UUID, adapter_key: str) -> ScraperAdapter:
        record = self._repository.get_by_key(organization_id, adapter_key)
        if record is not None:
            return record

        manifest = self._try_get_manifest(adapter_key)
        if manifest is None:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")

        now = datetime.now(tz=UTC)
        adapter = ScraperAdapter.create(
            organization_id=organization_id,
            adapter_key=adapter_key,
            name=manifest.display_name,
            description=manifest.notes or None,
            status=manifest.status,
            version=manifest.version,
            manifest=None,
            is_active=True,
            now=now,
        )
        return self._repository.add(adapter)

    def _try_get_manifest(self, adapter_key: str) -> ScraperManifest | None:
        try:
            return self._manager.get_manifest(adapter_key)
        except KeyError:
            return None

    def _merge_view(
        self,
        manifest: ScraperManifest | None,
        record: ScraperAdapter | None,
    ) -> ManagedAdapterView:
        if manifest is None:
            if record is None:
                raise AdapterNotFoundError("Adapter not found")
            return self._view_from_record(record, manifest=None)

        display_name = record.name if record is not None else manifest.display_name
        status = record.status.value if record is not None else manifest.status.value
        version = record.version if record is not None and record.version else manifest.version
        description = record.description if record is not None else manifest.notes or None
        is_active = record.is_active if record is not None else True
        manifest_json = record.manifest if record is not None else None
        last_verified_at = record.last_verified_at if record is not None else None
        last_verified = (
            last_verified_at.date().isoformat()
            if last_verified_at is not None
            else manifest.last_verified
        )

        return ManagedAdapterView(
            id=record.id if record is not None else None,
            adapter_key=manifest.adapter_key,
            display_name=display_name,
            description=description,
            status=status,
            version=version,
            features=build_adapter_features(manifest),
            last_verified=last_verified,
            actions_available=resolve_actions_available(manifest),
            is_active=is_active,
            manifest=manifest_json,
            last_verified_at=last_verified_at,
            is_registered=True,
            created_at=record.created_at if record is not None else None,
            updated_at=record.updated_at if record is not None else None,
        )

    def _view_from_record(
        self,
        record: ScraperAdapter,
        *,
        manifest: ScraperManifest | None = None,
    ) -> ManagedAdapterView:
        registry_manifest = manifest or self._try_get_manifest(record.adapter_key)
        features = build_adapter_features(registry_manifest) if registry_manifest else []
        actions = resolve_actions_available(registry_manifest) if registry_manifest else ["view"]
        last_verified = (
            record.last_verified_at.date().isoformat()
            if record.last_verified_at is not None
            else None
        )
        return ManagedAdapterView(
            id=record.id,
            adapter_key=record.adapter_key,
            display_name=record.name,
            description=record.description,
            status=record.status.value,
            version=record.version or "1.0.0",
            features=features,
            last_verified=last_verified,
            actions_available=actions,
            is_active=record.is_active,
            manifest=record.manifest,
            last_verified_at=record.last_verified_at,
            is_registered=registry_manifest is not None,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


def create_scraper_adapter_service(
    repository: ScraperAdapterRepository,
    manager: ScraperManager,
) -> ScraperAdapterService:
    return ScraperAdapterService(repository, manager)
