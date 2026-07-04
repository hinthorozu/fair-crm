"""Per-organization hides for built-in registry adapters after hard delete."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.scraper.infrastructure.persistence.models import ScraperRegistryAdapterHideModel


class ScraperRegistryAdapterHideRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_hide(self, organization_id: UUID, adapter_key: str) -> None:
        normalized_key = adapter_key.strip().lower()
        if self.is_hidden(organization_id, normalized_key):
            return
        self._session.add(
            ScraperRegistryAdapterHideModel(
                id=uuid4(),
                organization_id=organization_id,
                adapter_key=normalized_key,
                created_at=datetime.now(tz=UTC),
            )
        )
        self._session.flush()

    def remove_hide(self, organization_id: UUID, adapter_key: str) -> None:
        normalized_key = adapter_key.strip().lower()
        self._session.execute(
            delete(ScraperRegistryAdapterHideModel).where(
                ScraperRegistryAdapterHideModel.organization_id == organization_id,
                ScraperRegistryAdapterHideModel.adapter_key == normalized_key,
            )
        )
        self._session.flush()

    def is_hidden(self, organization_id: UUID, adapter_key: str) -> bool:
        normalized_key = adapter_key.strip().lower()
        stmt = (
            select(ScraperRegistryAdapterHideModel.id)
            .where(
                ScraperRegistryAdapterHideModel.organization_id == organization_id,
                ScraperRegistryAdapterHideModel.adapter_key == normalized_key,
            )
            .limit(1)
        )
        return self._session.scalar(stmt) is not None

    def list_hidden_keys(self, organization_id: UUID) -> list[str]:
        stmt = (
            select(ScraperRegistryAdapterHideModel.adapter_key)
            .where(ScraperRegistryAdapterHideModel.organization_id == organization_id)
            .order_by(ScraperRegistryAdapterHideModel.adapter_key.asc())
        )
        return list(self._session.scalars(stmt).all())
