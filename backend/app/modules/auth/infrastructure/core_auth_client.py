"""HTTP client for KYROX Core authentication endpoints (public API only)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CoreTokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class CoreAuthMessage:
    message: str


class CoreAuthError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class CoreAuthClient:
    """Thin proxy to Core /api/v1/auth/* — does not reimplement identity rules."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 15.0,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.kyrox_core_base_url).rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def login(self, *, email: str, password: str) -> CoreTokenPair:
        return self._post_token_pair(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

    def refresh(self, *, refresh_token: str) -> CoreTokenPair:
        return self._post_token_pair(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    def logout(self, *, refresh_token: str) -> None:
        url = f"{self._base_url}/api/v1/auth/logout"
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(url, json={"refresh_token": refresh_token})
        except httpx.RequestError as exc:
            logger.warning("Core logout unreachable: error=%s", type(exc).__name__)
            return
        if response.status_code not in {204, 200, 401}:
            logger.warning("Core logout unexpected status=%s", response.status_code)

    def signup(
        self,
        *,
        organization_name: str,
        email: str,
        organization_slug: str | None = None,
    ) -> CoreAuthMessage:
        payload = {
            "organization_name": organization_name,
            "email": email,
        }
        if organization_slug is not None:
            payload["organization_slug"] = organization_slug
        return self._post_message("/api/v1/auth/signup", json=payload)

    def complete_activation(self, *, token: str, password: str) -> CoreAuthMessage:
        return self._post_message(
            "/api/v1/auth/activation/complete",
            json={"token": token, "password": password},
        )

    def forgot_password(self, *, email: str) -> CoreAuthMessage:
        return self._post_message(
            "/api/v1/auth/password/forgot",
            json={"email": email},
        )

    def reset_password(self, *, token: str, password: str) -> CoreAuthMessage:
        return self._post_message(
            "/api/v1/auth/password/reset",
            json={"token": token, "password": password},
        )

    def change_password(
        self,
        *,
        access_token: str,
        current_password: str,
        new_password: str,
    ) -> CoreAuthMessage:
        return self._post_message(
            "/api/v1/auth/password/change",
            json={
                "current_password": current_password,
                "new_password": new_password,
            },
            access_token=access_token,
        )

    def _post_message(
        self,
        path: str,
        *,
        json: dict,
        access_token: str | None = None,
    ) -> CoreAuthMessage:
        url = f"{self._base_url}{path}"
        headers = None
        if access_token is not None:
            headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(url, json=json, headers=headers)
        except httpx.RequestError as exc:
            logger.warning("Core auth unreachable path=%s error=%s", path, type(exc).__name__)
            raise CoreAuthError("Authentication service unavailable", status_code=503) from exc

        if response.status_code >= 400:
            # Do not proxy provider/internal 5xx details through the product boundary.
            detail = (
                "Authentication service unavailable"
                if response.status_code >= 500
                else _safe_detail(response)
            )
            raise CoreAuthError(detail, status_code=response.status_code)

        try:
            data = response.json()
        except ValueError as exc:
            raise CoreAuthError("Invalid authentication response", status_code=502) from exc
        if not isinstance(data, dict):
            raise CoreAuthError("Invalid authentication response", status_code=502)
        message = data.get("message")
        if not isinstance(message, str) or not message.strip():
            raise CoreAuthError("Invalid authentication response", status_code=502)
        return CoreAuthMessage(message=message)

    def _post_token_pair(self, path: str, *, json: dict) -> CoreTokenPair:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(url, json=json)
        except httpx.RequestError as exc:
            logger.warning("Core auth unreachable path=%s error=%s", path, type(exc).__name__)
            raise CoreAuthError("Authentication service unavailable", status_code=503) from exc

        if response.status_code >= 400:
            detail = _safe_detail(response)
            raise CoreAuthError(detail, status_code=response.status_code)

        data = response.json()
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if not isinstance(access, str) or not isinstance(refresh, str):
            raise CoreAuthError("Invalid authentication response", status_code=502)

        settings = get_settings()
        expires_in = data.get("expires_in")
        if not isinstance(expires_in, int) or expires_in <= 0:
            expires_in = settings.access_token_expire_days * 24 * 60 * 60

        token_type = data.get("token_type")
        if not isinstance(token_type, str) or not token_type:
            token_type = "bearer"

        return CoreTokenPair(
            access_token=access,
            refresh_token=refresh,
            token_type=token_type,
            expires_in=expires_in,
        )


def _safe_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "Authentication failed"
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail:
            # Core public 4xx errors are contract-safe strings; secrets remain Core-owned.
            return detail
        message = payload.get("message")
        if isinstance(message, str) and message:
            return message
    return "Authentication failed"
