from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger
from app.integrations.kyrox_core.ports import AuthorizationPort

logger = get_logger(__name__)


class KyroxCoreHttpClient:
    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.kyrox_core_base_url).rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        access_token: str,
        organization_id: UUID,
        json: dict | None = None,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Organization-Id": str(organization_id),
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            return client.request(method, url, headers=headers, json=json)


class HttpAuthorizationAdapter(AuthorizationPort):
    def __init__(self, http_client: KyroxCoreHttpClient | None = None) -> None:
        self._http = http_client or KyroxCoreHttpClient()

    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = user_id
        path = f"/api/v1/organizations/{organization_id}/authorization/check"
        try:
            response = self._http.request(
                "POST",
                path,
                access_token=access_token,
                organization_id=organization_id,
                json={"permission_code": permission_code},
            )
        except httpx.RequestError as exc:
            logger.warning(
                "Core authorization check unreachable: permission=%s organization_id=%s error=%s",
                permission_code,
                organization_id,
                exc,
            )
            raise ForbiddenError("Authorization service unavailable") from exc
        if response.status_code == 403:
            return False
        if response.status_code >= 400:
            logger.warning(
                "Core authorization check failed: status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise ForbiddenError("Authorization check failed")
        data = response.json()
        return bool(data.get("allowed"))


class HttpAuditAdapter:
    """Best-effort audit writer for Sprint 1.

    Customer mutations must succeed even when Core audit API is unavailable.
    Failures are logged as warnings and never propagated to callers.
    """

    def __init__(self, http_client: KyroxCoreHttpClient | None = None) -> None:
        self._http = http_client or KyroxCoreHttpClient()

    def record_event(
        self,
        *,
        organization_id: UUID,
        access_token: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        path = f"/api/v1/organizations/{organization_id}/audit-events"
        body = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_values": old_values,
            "new_values": new_values,
            "metadata": metadata,
        }
        try:
            response = self._http.request(
                "POST",
                path,
                access_token=access_token,
                organization_id=organization_id,
                json=body,
            )
            if response.status_code >= 400:
                logger.warning(
                    "Best-effort Core audit write failed; CRM operation succeeded. "
                    "status=%s action=%s resource_type=%s resource_id=%s body=%s",
                    response.status_code,
                    action,
                    resource_type,
                    resource_id,
                    response.text,
                )
            else:
                logger.debug(
                    "Core audit event recorded: action=%s resource_type=%s resource_id=%s",
                    action,
                    resource_type,
                    resource_id,
                )
        except Exception as exc:
            logger.warning(
                "Best-effort Core audit write failed; CRM operation succeeded. "
                "action=%s resource_type=%s resource_id=%s error=%s",
                action,
                resource_type,
                resource_id,
                exc,
            )
