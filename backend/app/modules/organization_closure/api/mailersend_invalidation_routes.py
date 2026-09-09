from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.organization_closure.api.routes import (
    _access_token,
    _assert_target_context,
    _raise_http_error,
    get_closure_auth_context,
    get_closure_repository,
    get_credential_disposition_repository,
    get_email_account_repository,
    get_lifecycle_guard,
)
from app.modules.organization_closure.api.schemas import (
    OrganizationClosureCredentialDispositionResponse,
)
from app.modules.organization_closure.application.mailersend_invalidation import (
    MailerSendCredentialInvalidationService,
)
from app.modules.organization_closure.application.service import OrganizationClosureError
from app.modules.organization_closure.infrastructure.credential_disposition_repository import (
    SqlAlchemyOrganizationClosureCredentialDispositionRepository,
)
from app.modules.organization_closure.infrastructure.repository import (
    SqlAlchemyOrganizationClosureRepository,
)
from app.modules.system_admin.api.dependencies import (
    bearer_scheme,
    get_audit_adapter,
    get_authorization_adapter,
)

router = APIRouter(prefix="/system-admin", tags=["system-admin"])


def get_mailersend_invalidation_service(
    disposition_repository: SqlAlchemyOrganizationClosureCredentialDispositionRepository = Depends(
        get_credential_disposition_repository
    ),
    closure_repository: SqlAlchemyOrganizationClosureRepository = Depends(
        get_closure_repository
    ),
    email_accounts: SqlAlchemyEmailAccountRepository = Depends(
        get_email_account_repository
    ),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    lifecycle: OrganizationLifecycleGuard = Depends(get_lifecycle_guard),
    audit: AuditPort = Depends(get_audit_adapter),
) -> MailerSendCredentialInvalidationService:
    return MailerSendCredentialInvalidationService(
        disposition_repository,
        closure_repository,
        email_accounts,
        authorization,
        lifecycle,
        audit,
    )


@router.post(
    "/organizations/{organization_id}/closure-executions/{execution_id}"
    "/credential-dispositions/{disposition_id}/verify-mailersend-invalidation",
    response_model=OrganizationClosureCredentialDispositionResponse,
)
def verify_mailersend_invalidation(
    organization_id: UUID,
    execution_id: UUID,
    disposition_id: UUID,
    auth: AuthContext = Depends(get_closure_auth_context),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: MailerSendCredentialInvalidationService = Depends(
        get_mailersend_invalidation_service
    ),
) -> OrganizationClosureCredentialDispositionResponse:
    _assert_target_context(auth, organization_id)
    try:
        item = service.verify(
            organization_id=organization_id,
            execution_id=execution_id,
            disposition_id=disposition_id,
            auth=auth,
            access_token=_access_token(credentials),
        )
    except OrganizationClosureError as exc:
        _raise_http_error(exc)
    return OrganizationClosureCredentialDispositionResponse.model_validate(item)
