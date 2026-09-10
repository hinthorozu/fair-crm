from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

import httpx

from app.integrations.kyrox_core.client import KyroxCoreHttpClient

EXPECTED_SUSPENSION_EPISODE_HEADER = "X-Kyrox-Expected-Suspension-Updated-At"


class CoreOrganizationTombstoneError(RuntimeError):
    pass


class CoreOrganizationTombstoneUnavailableError(CoreOrganizationTombstoneError):
    pass


class CoreOrganizationTombstoneConflictError(CoreOrganizationTombstoneError):
    pass


class OrganizationTombstonePort(Protocol):
    def delete_suspended_episode(
        self,
        *,
        organization_id: UUID,
        expected_suspension_updated_at: datetime,
        access_token: str,
    ) -> None: ...


class KyroxCoreOrganizationTombstoneAdapter:
    def __init__(self, http_client: KyroxCoreHttpClient | None = None) -> None:
        self._http = http_client or KyroxCoreHttpClient()

    def delete_suspended_episode(
        self,
        *,
        organization_id: UUID,
        expected_suspension_updated_at: datetime,
        access_token: str,
    ) -> None:
        path = f"/api/v1/organizations/{organization_id}"
        try:
            response = self._http.request(
                "DELETE",
                path,
                access_token=access_token,
                organization_id=organization_id,
                extra_headers={
                    EXPECTED_SUSPENSION_EPISODE_HEADER: expected_suspension_updated_at.isoformat()
                },
            )
        except httpx.RequestError as exc:
            raise CoreOrganizationTombstoneUnavailableError(
                "Core organization tombstone authority unavailable"
            ) from exc

        if response.status_code == 204:
            return
        if response.status_code in {404, 409}:
            raise CoreOrganizationTombstoneConflictError(
                "Core organization tombstone precondition changed"
            )
        if response.status_code >= 500:
            raise CoreOrganizationTombstoneUnavailableError(
                "Core organization tombstone authority unavailable"
            )
        raise CoreOrganizationTombstoneConflictError(
            "Core organization tombstone request was rejected"
        )
