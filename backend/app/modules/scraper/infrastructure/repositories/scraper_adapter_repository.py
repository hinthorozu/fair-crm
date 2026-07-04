"""Repository for managed scraper adapter records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.scraper.domain.scraper_adapter import ScraperAdapter
from app.modules.scraper.domain.scraper_adapter_exceptions import DuplicateAdapterKeyError
from app.modules.scraper.infrastructure.persistence.scraper_adapter_mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.scraper.infrastructure.persistence.models import ScraperAdapterModel


class ScraperAdapterRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, adapter: ScraperAdapter) -> ScraperAdapter:
        model = entity_to_model(adapter)
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateAdapterKeyError(
                f"Adapter key already exists for organization: {adapter.adapter_key}"
            ) from exc
        return model_to_entity(model)

    def update(self, adapter: ScraperAdapter) -> ScraperAdapter:
        model = self._session.get(ScraperAdapterModel, adapter.id)
        if model is None:
            raise ValueError(f"Adapter not found: {adapter.id}")
        update_model_from_entity(model, adapter)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateAdapterKeyError(
                f"Adapter key already exists for organization: {adapter.adapter_key}"
            ) from exc
        return model_to_entity(model)

    def get_by_key(
        self,
        organization_id: UUID,
        adapter_key: str,
        *,
        include_deleted: bool = False,
    ) -> ScraperAdapter | None:
        stmt = select(ScraperAdapterModel).where(
            ScraperAdapterModel.organization_id == organization_id,
            ScraperAdapterModel.adapter_key == adapter_key,
        )
        if not include_deleted:
            stmt = stmt.where(ScraperAdapterModel.deleted_at.is_(None))
        model = self._session.scalars(stmt).first()
        return model_to_entity(model) if model is not None else None

    def list_by_organization(self, organization_id: UUID) -> list[ScraperAdapter]:
        stmt = (
            select(ScraperAdapterModel)
            .where(
                ScraperAdapterModel.organization_id == organization_id,
                ScraperAdapterModel.deleted_at.is_(None),
            )
            .order_by(ScraperAdapterModel.adapter_key.asc())
        )
        return [model_to_entity(model) for model in self._session.scalars(stmt).all()]

    def hard_delete_by_key(self, organization_id: UUID, adapter_key: str) -> int:
        normalized_key = adapter_key.strip().lower()
        result = self._session.execute(
            delete(ScraperAdapterModel).where(
                ScraperAdapterModel.organization_id == organization_id,
                ScraperAdapterModel.adapter_key == normalized_key,
            )
        )
        self._session.flush()
        return int(result.rowcount or 0)
