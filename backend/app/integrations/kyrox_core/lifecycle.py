from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger

logger = get_logger(__name__)

_VALID_STATUSES = {"pending_activation", "active", "suspended", "archived"}


class OrganizationLifecycleUnavailableError(ForbiddenError):
    """Canonical Core lifecycle eligibility could not be established."""


class OrganizationWorkNotAllowedError(ForbiddenError):
    """Canonical Core lifecycle state explicitly prohibits product work."""


@dataclass(frozen=True, slots=True)
class OrganizationLifecycleSnapshot:
    organization_id: UUID
    status: str
    work_allowed: bool


class KyroxCoreLifecycleClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        lifecycle_token: str | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.kyrox_core_base_url).rstrip("/")
        self._lifecycle_token = lifecycle_token or settings.kyrox_core_product_lifecycle_token

    def get_snapshot(self, organization_id: UUID) -> httpx.Response:
        url = f"{self._base_url}/api/v1/organizations/{organization_id}/lifecycle-snapshot"
        headers = {
            "X-Kyrox-Product-Lifecycle-Token": self._lifecycle_token,
            "Accept": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            return client.get(url, headers=headers)


class OrganizationLifecycleGuard:
    """Fail-closed read adapter for Core-owned organization lifecycle eligibility.

    This guard deliberately does not cache or persist Core lifecycle state. Callers
    choose explicit job/side-effect checkpoints; OL07-04+ owns those call sites.
    """

    def __init__(self, client: KyroxCoreLifecycleClient | None = None) -> None:
        self._client = client or KyroxCoreLifecycleClient()

    def get_snapshot(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        try:
            response = self._client.get_snapshot(organization_id)
        except httpx.RequestError as exc:
            logger.warning(
                "Core lifecycle snapshot unreachable: organization_id=%s error=%s",
                organization_id,
                exc,
            )
            raise OrganizationLifecycleUnavailableError(
                "Organization lifecycle authority unavailable"
            ) from exc

        if response.status_code != 200:
            logger.warning(
                "Core lifecycle snapshot failed: organization_id=%s status=%s body=%s",
                organization_id,
                response.status_code,
                response.text,
            )
            raise OrganizationLifecycleUnavailableError(
                "Organization lifecycle authority check failed"
            )

        try:
            data = response.json()
            returned_organization_id = UUID(str(data["organization_id"]))
            lifecycle_status = data["status"]
            work_allowed = data["work_allowed"]
        except (KeyError, TypeError, ValueError) as exc:
            raise OrganizationLifecycleUnavailableError(
                "Organization lifecycle authority returned an invalid response"
            ) from exc

        if returned_organization_id != organization_id:
            raise OrganizationLifecycleUnavailableError(
                "Organization lifecycle authority returned the wrong organization"
            )
        if lifecycle_status not in _VALID_STATUSES or type(work_allowed) is not bool:
            raise OrganizationLifecycleUnavailableError(
                "Organization lifecycle authority returned an invalid response"
            )
        if work_allowed != (lifecycle_status == "active"):
            raise OrganizationLifecycleUnavailableError(
                "Organization lifecycle authority returned an inconsistent response"
            )

        return OrganizationLifecycleSnapshot(
            organization_id=returned_organization_id,
            status=lifecycle_status,
            work_allowed=work_allowed,
        )

    def require_work_allowed(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        snapshot = self.get_snapshot(organization_id)
        if not snapshot.work_allowed:
            raise OrganizationWorkNotAllowedError(
                f"Organization lifecycle does not allow product work: {snapshot.status}"
            )
        return snapshot
