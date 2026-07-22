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


class CoreAuthError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class CoreAuthClient:
    """Thin proxy to Core /api/v1/auth/* — does not reimplement token issuance."""

    def __init__(self, base_url: str | None = None, timeout: float = 15.0) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.kyrox_core_base_url).rstrip("/")
        self._timeout = timeout

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
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json={"refresh_token": refresh_token})
        except httpx.RequestError as exc:
            logger.warning("Core logout unreachable: error=%s", type(exc).__name__)
            return
        if response.status_code not in {204, 200, 401}:
            logger.warning("Core logout unexpected status=%s", response.status_code)

    def _post_token_pair(self, path: str, *, json: dict) -> CoreTokenPair:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
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
            # Never echo raw tokens; Core error messages are safe strings.
            return detail
        message = payload.get("message")
        if isinstance(message, str) and message:
            return message
    return "Authentication failed"
