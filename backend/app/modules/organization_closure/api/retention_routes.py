from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.audit_retention import KyroxCoreAuditRetentionAdapter
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.integrations.kyrox_core.ports import AuthContext, AuthorizationPort
from app.modules.organization_closure.api.routes import (
    _access_token,
    _assert_target_context,
    _raise_http_error,
    get_closure_auth_context,
    get_lifecycle_guard,
)
from app.modules.organization_closure.application.evidence_retention import (
    OrganizationClosureEvidenceRetentionService,
)
from app.modules.organization_closure.application.service import OrganizationClosureError
from app.modules.organization_closure.infrastructure.evidence_retention_repository import (
    SqlAlchemyOrganizationClosureEvidenceRetentionRepository,
)
from app.modules.system_admin.api.dependencies import bearer_scheme, get_authorization_adapter

router = APIRouter(prefix="/system-admin", tags=["system-admin"])


class OrganizationClosureEvidenceRetentionResponse(BaseModel):
    organization_id: UUID
    terminal_closed_at: datetime
    retention_deadline: datetime
    core_audit_purged_count: int
    local_purge_counts: dict[str, int]
    total_local_purged_count: int


def get_core_audit_retention_adapter() -> KyroxCoreAuditRetentionAdapter:
    return KyroxCoreAuditRetentionAdapter()


def get_evidence_retention_service(
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    lifecycle: OrganizationLifecycleGuard = Depends(get_lifecycle_guard),
    core_audit_retention: KyroxCoreAuditRetentionAdapter = Depends(
        get_core_audit_retention_adapter
    ),
) -> OrganizationClosureEvidenceRetentionService:
    return OrganizationClosureEvidenceRetentionService(
        SqlAlchemyOrganizationClosureEvidenceRetentionRepository(db),
        authorization,
        lifecycle,
        core_audit_retention,
    )


@router.post(
    "/organizations/{organization_id}/closure-retention/purge",
    response_model=OrganizationClosureEvidenceRetentionResponse,
)
def purge_organization_closure_retained_evidence(
    organization_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: OrganizationClosureEvidenceRetentionService = Depends(
        get_evidence_retention_service
    ),
) -> OrganizationClosureEvidenceRetentionResponse:
    _assert_target_context(auth, organization_id)
    try:
        result = service.purge(
            organization_id=organization_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)

    return OrganizationClosureEvidenceRetentionResponse(
        organization_id=result.organization_id,
        terminal_closed_at=result.terminal_closed_at,
        retention_deadline=result.retention_deadline,
        core_audit_purged_count=result.core_audit_purged_count,
        local_purge_counts=result.local_purge_counts.as_dict(),
        total_local_purged_count=result.local_purge_counts.total,
    )
