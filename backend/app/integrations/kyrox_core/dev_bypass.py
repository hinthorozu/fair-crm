"""Local development bypass for running Fair CRM without KYROX Core."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.kyrox_core.auth import build_auth_context
from app.integrations.kyrox_core.ports import AuthContext, AuthorizationPort

logger = get_logger(__name__)

DEFAULT_DEV_BYPASS_TOKEN = "dev-bypass"


def dev_bypass_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return settings.dev_bypass_core and settings.app_env in {"development", "local", "test"}


def validate_dev_bypass_settings(settings: Settings) -> None:
    if settings.dev_bypass_core and settings.app_env not in {"development", "local", "test"}:
        raise RuntimeError(
            "FAIR_CRM_DEV_BYPASS_CORE is only allowed when APP_ENV is development, local, or test"
        )


class AllowAllAuthorizationAdapter(AuthorizationPort):
    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (organization_id, user_id, permission_code, access_token)
        return True


class NoOpAuditAdapter:
    def record_event(self, **kwargs) -> None:
        logger.debug("Dev bypass: audit write skipped (%s)", kwargs.get("action"))


def resolve_auth_context(
    credentials: HTTPAuthorizationCredentials | None,
    organization_id: UUID,
    *,
    dev_user_id: UUID | None = None,
) -> AuthContext:
    settings = get_settings()

    if credentials and credentials.credentials:
        bypass_token = settings.dev_bypass_token or DEFAULT_DEV_BYPASS_TOKEN
        if dev_bypass_enabled(settings) and credentials.credentials == bypass_token:
            user_id = dev_user_id or settings.dev_user_id or uuid4()
            return AuthContext(
                user_id=user_id,
                email=settings.dev_user_email,
                session_id=uuid4(),
                organization_id=organization_id,
            )
        try:
            return build_auth_context(credentials.credentials, organization_id)
        except Exception:
            if not dev_bypass_enabled(settings):
                raise

    if dev_bypass_enabled(settings):
        user_id = dev_user_id or settings.dev_user_id or uuid4()
        return AuthContext(
            user_id=user_id,
            email=settings.dev_user_email,
            session_id=uuid4(),
            organization_id=organization_id,
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def log_dev_bypass_startup_warning() -> None:
    if dev_bypass_enabled():
        logger.warning(
            "FAIR_CRM_DEV_BYPASS_CORE is enabled — Core authorization and audit are bypassed. "
            "Use Authorization: Bearer %s with X-Organization-Id for local testing only.",
            get_settings().dev_bypass_token or DEFAULT_DEV_BYPASS_TOKEN,
        )
