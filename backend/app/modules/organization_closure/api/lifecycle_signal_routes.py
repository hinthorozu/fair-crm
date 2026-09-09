from __future__ import annotations

import os
from datetime import datetime
from secrets import compare_digest
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.organization_closure.application.suspension_security import (
    OrganizationSuspensionSecurityService,
)

router = APIRouter(prefix="/internal/lifecycle-security", tags=["internal-lifecycle-security"])

_DEFAULT_SIGNAL_TOKEN = "dev-insecure-lifecycle-signal-token-change-me"


class OrganizationSuspendedSignal(BaseModel):
    organization_id: UUID
    lifecycle_updated_at: datetime


class OrganizationSuspendedSignalResponse(BaseModel):
    outcome: str
    zeroized_signing_secrets: int


def require_lifecycle_signal_credential(
    token: str | None = Header(default=None, alias="X-Kyrox-Lifecycle-Signal-Token"),
) -> None:
    expected = os.getenv(
        "FAIR_CRM_CORE_LIFECYCLE_SIGNAL_TOKEN",
        _DEFAULT_SIGNAL_TOKEN,
    )
    if token is None or not compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid lifecycle signal credential",
        )


def get_suspension_security_service(
    db: Session = Depends(get_db),
) -> OrganizationSuspensionSecurityService:
    return OrganizationSuspensionSecurityService(
        SqlAlchemyEmailAccountRepository(db),
        OrganizationLifecycleGuard(),
    )


@router.post(
    "/organization-suspended",
    response_model=OrganizationSuspendedSignalResponse,
    dependencies=[Depends(require_lifecycle_signal_credential)],
    responses={401: {"description": "Invalid lifecycle signal credential"}, 503: {"description": "Core lifecycle authority unavailable"}},
)
def organization_suspended(
    payload: OrganizationSuspendedSignal,
    service: OrganizationSuspensionSecurityService = Depends(
        get_suspension_security_service
    ),
) -> OrganizationSuspendedSignalResponse:
    try:
        result = service.apply(
            organization_id=payload.organization_id,
            lifecycle_updated_at=payload.lifecycle_updated_at,
        )
    except OrganizationLifecycleUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Core lifecycle authority unavailable",
        ) from exc
    return OrganizationSuspendedSignalResponse(
        outcome=result.outcome,
        zeroized_signing_secrets=result.zeroized_signing_secrets,
    )
