"""Persistence mappers for managed scraper adapters."""

from app.modules.scraper.domain.scraper_adapter import ScraperAdapter
from app.modules.scraper.infrastructure.persistence.models import ScraperAdapterModel
from app.modules.scraper.manifests.scraper_manifest import ScraperStatus


def model_to_entity(model: ScraperAdapterModel) -> ScraperAdapter:
    return ScraperAdapter(
        id=model.id,
        organization_id=model.organization_id,
        adapter_key=model.adapter_key,
        name=model.name,
        description=model.description,
        status=ScraperStatus(model.status),
        version=model.version,
        manifest=model.manifest,
        is_active=model.is_active,
        last_verified_at=model.last_verified_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def entity_to_model(adapter: ScraperAdapter) -> ScraperAdapterModel:
    return ScraperAdapterModel(
        id=adapter.id,
        organization_id=adapter.organization_id,
        adapter_key=adapter.adapter_key,
        name=adapter.name,
        description=adapter.description,
        status=adapter.status.value,
        version=adapter.version,
        manifest=adapter.manifest,
        is_active=adapter.is_active,
        last_verified_at=adapter.last_verified_at,
        created_at=adapter.created_at,
        updated_at=adapter.updated_at,
        deleted_at=adapter.deleted_at,
    )


def update_model_from_entity(model: ScraperAdapterModel, adapter: ScraperAdapter) -> None:
    model.name = adapter.name
    model.description = adapter.description
    model.status = adapter.status.value
    model.version = adapter.version
    model.manifest = adapter.manifest
    model.is_active = adapter.is_active
    model.last_verified_at = adapter.last_verified_at
    model.updated_at = adapter.updated_at
    model.deleted_at = adapter.deleted_at
