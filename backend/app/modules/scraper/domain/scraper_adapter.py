"""Managed adapter record stored per organization."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.modules.scraper.domain.scraper_adapter_exceptions import (
    InvalidAdapterKeyError,
    InvalidAdapterNameError,
)
from app.modules.scraper.manifests.scraper_manifest import ScraperStatus

ADAPTER_KEY_PATTERN = re.compile(r"^[a-z0-9_]+$")


def normalize_adapter_key(value: str) -> str:
    key = value.strip().lower()
    if not key or not ADAPTER_KEY_PATTERN.fullmatch(key):
        raise InvalidAdapterKeyError("adapter_key must contain only lowercase letters, numbers, and underscores")
    return key


@dataclass
class ScraperAdapter:
    id: UUID
    organization_id: UUID
    adapter_key: str
    name: str
    description: str | None
    status: ScraperStatus
    version: str | None
    manifest: dict[str, Any] | None
    is_active: bool
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        adapter_key: str,
        name: str,
        description: str | None = None,
        status: ScraperStatus = ScraperStatus.EXPERIMENTAL,
        version: str | None = None,
        manifest: dict[str, Any] | None = None,
        is_active: bool = True,
        last_verified_at: datetime | None = None,
        now: datetime,
    ) -> ScraperAdapter:
        normalized_key = normalize_adapter_key(adapter_key)
        trimmed_name = name.strip()
        if not trimmed_name:
            raise InvalidAdapterNameError("name must not be empty")

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            adapter_key=normalized_key,
            name=trimmed_name,
            description=description.strip() if description else None,
            status=status,
            version=version.strip() if version else None,
            manifest=manifest,
            is_active=is_active,
            last_verified_at=last_verified_at,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    def update_fields(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        status: ScraperStatus | None = None,
        version: str | None = None,
        manifest: dict[str, Any] | None = None,
        is_active: bool | None = None,
        last_verified_at: datetime | None = None,
        now: datetime,
    ) -> None:
        if name is not None:
            trimmed = name.strip()
            if not trimmed:
                raise InvalidAdapterNameError("name must not be empty")
            self.name = trimmed
        if description is not None:
            self.description = description.strip() if description else None
        if status is not None:
            self.status = status
        if version is not None:
            self.version = version.strip() if version else None
        if manifest is not None:
            self.manifest = manifest
        if is_active is not None:
            self.is_active = is_active
        if last_verified_at is not None:
            self.last_verified_at = last_verified_at
        self.updated_at = now

    def activate(self, *, now: datetime) -> None:
        self.is_active = True
        self.updated_at = now

    def deactivate(self, *, now: datetime) -> None:
        self.is_active = False
        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        self.deleted_at = now
        self.is_active = False
        self.updated_at = now
