from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CoreAuditRetentionUnavailableError(Exception):
    pass


class CoreAuditRetentionPreconditionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CoreAuditRetentionResult:
    organization_id: UUID
    terminal_deleted_at: datetime
    retention_deadline: datetime
    purged_count: int


class KyroxCoreAuditRetentionClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        lifecycle_token: str | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.kyrox_core_base_url).rstrip("/")
        self._lifecycle_token = lifecycle_token or settings.kyrox_core_product_lifecycle_token

    def purge(self, organization_id: UUID) -> httpx.Response:
        url = (
            f"{self._base_url}/api/v1/organizations/{organization_id}/"
            "retained-audit-evidence/purge"
        )
        headers = {
            "X-Kyrox-Product-Lifecycle-Token": self._lifecycle_token,
            "Accept": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            return client.post(url, headers=headers)


class KyroxCoreAuditRetentionAdapter:
    def __init__(self, client: KyroxCoreAuditRetentionClient | None = None) -> None:
        self._client = client or KyroxCoreAuditRetentionClient()

    def purge(self, organization_id: UUID) -> CoreAuditRetentionResult:
        try:
            response = self._client.purge(organization_id)
        except httpx.RequestError as exc:
            raise CoreAuditRetentionUnavailableError(
                "Core retained-audit authority unavailable"
            ) from exc

        if response.status_code in {404, 409}:
            raise CoreAuditRetentionPreconditionError(
                "Core retained-audit purge precondition is not satisfied"
            )
        if response.status_code != 200:
            logger.warning(
                "Core retained-audit purge failed: organization_id=%s status=%s body=%s",
                organization_id,
                response.status_code,
                response.text,
            )
            raise CoreAuditRetentionUnavailableError(
                "Core retained-audit purge failed"
            )

        try:
            data = response.json()
            returned_organization_id = UUID(str(data["organization_id"]))
            terminal_deleted_at = datetime.fromisoformat(
                str(data["terminal_deleted_at"]).replace("Z", "+00:00")
            )
            retention_deadline = datetime.fromisoformat(
                str(data["retention_deadline"]).replace("Z", "+00:00")
            )
            purged_count = data["purged_count"]
        except (KeyError, TypeError, ValueError) as exc:
            raise CoreAuditRetentionUnavailableError(
                "Core retained-audit authority returned an invalid response"
            ) from exc

        if (
            returned_organization_id != organization_id
            or terminal_deleted_at.tzinfo is None
            or terminal_deleted_at.utcoffset() is None
            or retention_deadline.tzinfo is None
            or retention_deadline.utcoffset() is None
            or type(purged_count) is not int
            or purged_count < 0
        ):
            raise CoreAuditRetentionUnavailableError(
                "Core retained-audit authority returned an inconsistent response"
            )

        return CoreAuditRetentionResult(
            organization_id=returned_organization_id,
            terminal_deleted_at=terminal_deleted_at,
            retention_deadline=retention_deadline,
            purged_count=purged_count,
        )
