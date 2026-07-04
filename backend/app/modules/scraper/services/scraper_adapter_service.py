"""CRUD and merge logic for managed scraper adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.domain.adapter_engine import AdapterEngineType
from app.modules.scraper.domain.scraper_adapter import (
    ScraperAdapter,
    allocate_adapter_key,
    normalize_adapter_key,
    slugify_adapter_key,
)
from app.modules.scraper.domain.scraper_adapter_exceptions import (
    AdapterEngineNotFoundError,
    AdapterNotFoundError,
    DuplicateAdapterKeyError,
)
from app.modules.scraper.domain.requested_output_fields import (
    normalize_requested_fields,
    requested_fields_from_overlay,
)
from app.modules.scraper.infrastructure.repositories.scraper_adapter_repository import (
    ScraperAdapterRepository,
)
from app.modules.scraper.infrastructure.repositories.scraper_registry_adapter_hide_repository import (
    ScraperRegistryAdapterHideRepository,
)
from app.modules.scraper.manifests.scraper_manifest import ScraperManifest, ScraperStatus
from app.modules.scraper.services.adapter_engine_service import AdapterEngineService, create_adapter_engine_service
from app.modules.scraper.services.manifest_overlay import (
    build_manifest_overlay_patch,
    merge_manifest_with_record,
    parse_last_verified,
)
from app.modules.scraper.services.scraper_dashboard_service import (
    build_adapter_features,
    resolve_actions_available,
)


@dataclass(frozen=True)
class ManagedAdapterView:
    id: UUID | None
    adapter_key: str
    engine_key: str
    engine_type: str
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
        hide_repository: ScraperRegistryAdapterHideRepository,
        engine_service: AdapterEngineService | None = None,
    ) -> None:
        self._repository = repository
        self._manager = manager
        self._hide_repository = hide_repository
        self._engine_service = engine_service or create_adapter_engine_service()

    def list_adapters(self, organization_id: UUID) -> list[ManagedAdapterView]:
        db_by_key = {
            record.adapter_key: record for record in self._repository.list_by_organization(organization_id)
        }
        hidden_keys = set(self._hide_repository.list_hidden_keys(organization_id))
        results: list[ManagedAdapterView] = []
        seen: set[str] = set()

        for manifest in self._manager.list_manifests():
            if manifest.adapter_key in hidden_keys:
                continue
            record = db_by_key.get(manifest.adapter_key)
            results.append(self._merge_view(manifest, record, instance_key=manifest.adapter_key))
            seen.add(manifest.adapter_key)

        for key, record in db_by_key.items():
            if key not in seen:
                results.append(self._view_from_record(record, manifest=None))

        return results

    def get_adapter(self, organization_id: UUID, adapter_key: str) -> ManagedAdapterView:
        normalized_key = normalize_adapter_key(adapter_key)
        if self._hide_repository.is_hidden(organization_id, normalized_key):
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")
        record = self._repository.get_by_key(organization_id, normalized_key)
        engine_manifest = self._resolve_engine_manifest(record, normalized_key)
        if record is None and engine_manifest is None:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")
        return (
            self._merge_view(engine_manifest, record, instance_key=normalized_key)
            if engine_manifest is not None
            else self._view_from_record(record)
        )

    def create_adapter(
        self,
        organization_id: UUID,
        *,
        name: str,
        description: str | None = None,
        engine_key: str | None = None,
        requested_fields: list[str] | None = None,
        adapter_key: str | None = None,
        status: ScraperStatus = ScraperStatus.EXPERIMENTAL,
        version: str | None = None,
        manifest: dict[str, Any] | None = None,
        is_active: bool = True,
    ) -> ManagedAdapterView:
        reserved_keys = self._reserved_adapter_keys(organization_id)
        if adapter_key:
            normalized_key = normalize_adapter_key(adapter_key)
        else:
            normalized_key = allocate_adapter_key(slugify_adapter_key(name), reserved_keys)

        if engine_key:
            normalized_engine = normalize_adapter_key(engine_key)
            if self._engine_type_for_key(normalized_engine) != AdapterEngineType.STATIC:
                raise AdapterEngineNotFoundError(f"Adapter engine not found: {engine_key}")
            self._validate_engine_key(normalized_engine, instance_key=normalized_key)
        else:
            normalized_engine = normalized_key

        if normalized_key in reserved_keys:
            raise DuplicateAdapterKeyError(f"Adapter key already exists for organization: {normalized_key}")

        manifest_payload = dict(manifest or {})
        if requested_fields is not None:
            manifest_payload["requested_fields"] = normalize_requested_fields(requested_fields)

        self._repository.hard_delete_by_key(organization_id, normalized_key)
        self._hide_repository.remove_hide(organization_id, normalized_key)

        now = datetime.now(tz=UTC)
        adapter = ScraperAdapter.create(
            organization_id=organization_id,
            adapter_key=normalized_key,
            engine_key=normalized_engine,
            name=name,
            description=description,
            status=status,
            version=version,
            manifest=manifest_payload or None,
            is_active=is_active,
            now=now,
        )
        saved = self._repository.add(adapter)
        engine_manifest = self._try_get_manifest(saved.engine_key)
        return (
            self._merge_view(engine_manifest, saved, instance_key=saved.adapter_key)
            if engine_manifest is not None
            else self._view_from_record(saved)
        )

    def _reserved_adapter_keys(self, organization_id: UUID) -> set[str]:
        return {record.adapter_key for record in self._repository.list_by_organization(organization_id)}

    def get_merged_manifest(self, organization_id: UUID, adapter_key: str) -> ScraperManifest:
        normalized_key = normalize_adapter_key(adapter_key)
        if self._hide_repository.is_hidden(organization_id, normalized_key):
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")
        record = self._repository.get_by_key(organization_id, normalized_key)
        engine_manifest = self._resolve_engine_manifest(record, normalized_key)
        if engine_manifest is None:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")
        return merge_manifest_with_record(engine_manifest, record)

    def resolve_requested_fields(self, organization_id: UUID, adapter_key: str) -> list[str]:
        normalized_key = normalize_adapter_key(adapter_key)
        record = self._repository.get_by_key(organization_id, normalized_key)
        return requested_fields_from_overlay(record.manifest if record is not None else None)

    def update_adapter_manifest(
        self,
        organization_id: UUID,
        adapter_key: str,
        updates: dict[str, Any],
    ) -> ScraperManifest:
        normalized_key = normalize_adapter_key(adapter_key)
        record = self._repository.get_by_key(organization_id, normalized_key)
        if record is None:
            record = self._get_or_create_overlay(organization_id, normalized_key)
        engine_manifest = self._resolve_engine_manifest(record, normalized_key)
        if engine_manifest is None:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")
        now = datetime.now(tz=UTC)

        update_kwargs: dict[str, Any] = {"now": now}
        if "display_name" in updates:
            update_kwargs["name"] = updates["display_name"]
        if "notes" in updates:
            update_kwargs["description"] = updates["notes"]
        if "version" in updates:
            update_kwargs["version"] = updates["version"]
        if "last_verified" in updates:
            update_kwargs["last_verified_at"] = parse_last_verified(updates["last_verified"])

        if any(
            key in updates
            for key in ("supported_sites", "output", "browser", "supports", "requested_fields")
        ):
            requested_fields = updates.get("requested_fields")
            if requested_fields is not None:
                requested_fields = normalize_requested_fields(requested_fields)
            update_kwargs["manifest"] = build_manifest_overlay_patch(
                record.manifest,
                supported_sites=updates.get("supported_sites"),
                output=updates.get("output"),
                browser=updates.get("browser"),
                supports=updates.get("supports"),
                requested_fields=requested_fields,
            )

        record.update_fields(**update_kwargs)
        saved = self._repository.update(record)
        return merge_manifest_with_record(engine_manifest, saved)

    def update_adapter(
        self,
        organization_id: UUID,
        adapter_key: str,
        *,
        name: str | None = None,
        description: str | None = None,
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
            version=version,
            manifest=manifest,
            is_active=is_active,
            now=now,
        )
        saved = self._repository.update(record)
        engine_manifest = self._try_get_manifest(saved.engine_key)
        return (
            self._merge_view(engine_manifest, saved, instance_key=saved.adapter_key)
            if engine_manifest is not None
            else self._view_from_record(saved)
        )

    def activate_adapter(self, organization_id: UUID, adapter_key: str) -> ManagedAdapterView:
        record = self._get_or_create_overlay(organization_id, normalize_adapter_key(adapter_key))
        record.activate(now=datetime.now(tz=UTC))
        saved = self._repository.update(record)
        engine_manifest = self._try_get_manifest(saved.engine_key)
        return (
            self._merge_view(engine_manifest, saved, instance_key=saved.adapter_key)
            if engine_manifest is not None
            else self._view_from_record(saved)
        )

    def deactivate_adapter(self, organization_id: UUID, adapter_key: str) -> ManagedAdapterView:
        record = self._get_or_create_overlay(organization_id, normalize_adapter_key(adapter_key))
        record.deactivate(now=datetime.now(tz=UTC))
        saved = self._repository.update(record)
        engine_manifest = self._try_get_manifest(saved.engine_key)
        return (
            self._merge_view(engine_manifest, saved, instance_key=saved.adapter_key)
            if engine_manifest is not None
            else self._view_from_record(saved)
        )

    def hard_delete_adapter(self, organization_id: UUID, adapter_key: str) -> None:
        normalized_key = normalize_adapter_key(adapter_key)
        record = self._repository.get_by_key(organization_id, normalized_key)
        manifest = self._try_get_manifest(normalized_key)

        if record is None and manifest is None:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_key}")

        self._repository.hard_delete_by_key(organization_id, normalized_key)

        if manifest is not None:
            self._hide_repository.add_hide(organization_id, normalized_key)

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
            engine_key=manifest.adapter_key,
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

    def _validate_engine_key(self, engine_key: str, *, instance_key: str) -> None:
        if self._try_get_manifest(engine_key) is not None:
            return
        if engine_key == instance_key:
            return
        raise AdapterEngineNotFoundError(f"Adapter engine not found: {engine_key}")

    def _resolve_engine_manifest(
        self,
        record: ScraperAdapter | None,
        instance_key: str,
    ) -> ScraperManifest | None:
        if record is not None:
            manifest = self._try_get_manifest(record.engine_key)
            if manifest is not None:
                return manifest
        return self._try_get_manifest(instance_key)

    def _engine_type_for_key(self, engine_key: str) -> AdapterEngineType:
        manifest = self._try_get_manifest(engine_key)
        if manifest is not None:
            return manifest.engine_type
        return AdapterEngineType.DYNAMIC

    def _merge_view(
        self,
        manifest: ScraperManifest | None,
        record: ScraperAdapter | None,
        *,
        instance_key: str | None = None,
    ) -> ManagedAdapterView:
        if manifest is None:
            if record is None:
                raise AdapterNotFoundError("Adapter not found")
            return self._view_from_record(record)

        merged = merge_manifest_with_record(manifest, record)
        resolved_instance_key = instance_key or (record.adapter_key if record is not None else manifest.adapter_key)
        engine_key = record.engine_key if record is not None else manifest.adapter_key
        engine_type = self._engine_type_for_key(engine_key)
        display_name = record.name if record is not None else merged.display_name
        status = record.status.value if record is not None else merged.status.value
        version = record.version or merged.version if record is not None else merged.version
        description = record.description if record is not None else (merged.notes or None)
        is_active = record.is_active if record is not None else True
        manifest_json = record.manifest if record is not None else None
        last_verified_at = record.last_verified_at if record is not None else None
        last_verified = merged.last_verified

        return ManagedAdapterView(
            id=record.id if record is not None else None,
            adapter_key=resolved_instance_key,
            engine_key=engine_key,
            engine_type=engine_type.value,
            display_name=display_name,
            description=description,
            status=status,
            version=version,
            features=build_adapter_features(merged),
            last_verified=last_verified,
            actions_available=resolve_actions_available(merged),
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
        registry_manifest = manifest or self._try_get_manifest(record.engine_key)
        engine_type = self._engine_type_for_key(record.engine_key)
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
            engine_key=record.engine_key,
            engine_type=engine_type.value,
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
    hide_repository: ScraperRegistryAdapterHideRepository | None = None,
) -> ScraperAdapterService:
    hide_repo = hide_repository or ScraperRegistryAdapterHideRepository(repository._session)
    return ScraperAdapterService(repository, manager, hide_repo)
