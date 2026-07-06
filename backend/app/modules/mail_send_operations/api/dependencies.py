from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuthorizationAdapter
from app.integrations.kyrox_core.dev_bypass import (
    AllowAllAuthorizationAdapter,
    dev_bypass_enabled,
    resolve_auth_context,
)
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.mail_send_operations.application.list_mail_send_operations import (
    ListMailSendOperationsUseCase,
    PERMISSION_READ,
)
from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.application.retry_mail_send_operation import (
    PERMISSION_UPDATE,
    RetryMailSendOperationUseCase,
)
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
    SqlAlchemyMailTemplateRepository,
)
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import SqlAlchemySmtpAccountRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_authorization_adapter() -> AuthorizationPort:
    if dev_bypass_enabled():
        return AllowAllAuthorizationAdapter()
    return HttpAuthorizationAdapter()


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    organization_id: UUID = Header(..., alias="X-Organization-Id"),
    dev_user_id: UUID | None = Header(default=None, alias="X-Dev-User-Id"),
) -> AuthContext:
    try:
        return resolve_auth_context(credentials, organization_id, dev_user_id=dev_user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc


def require_read_permission(
    auth: AuthContext = Depends(get_auth_context),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_READ,
        access_token=credentials.credentials,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return auth


def require_update_permission(
    auth: AuthContext = Depends(get_auth_context),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_UPDATE,
        access_token=credentials.credentials,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return auth


def get_mail_send_operation_service(
    db: Session = Depends(get_db),
) -> MailSendOperationService:
    return MailSendOperationService(SqlAlchemyMailSendOperationRepository(db))


def get_list_mail_send_operations_use_case(
    db: Session = Depends(get_db),
) -> ListMailSendOperationsUseCase:
    return ListMailSendOperationsUseCase(
        SqlAlchemyMailSendOperationRepository(db),
        SqlAlchemySmtpAccountRepository(db),
        SqlAlchemyMailTemplateRepository(db),
        SqlAlchemyFairRepository(db),
        SqlAlchemyCustomerRepository(db),
    )


def get_retry_mail_send_operation_use_case(
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> RetryMailSendOperationUseCase:
    repository = SqlAlchemyMailSendOperationRepository(db)
    return RetryMailSendOperationUseCase(
        repository,
        MailSendOperationService(repository),
        SqlAlchemySmtpAccountRepository(db),
        SqlAlchemyMailTemplateRepository(db),
        SqlAlchemyFairRepository(db),
        SqlAlchemyCustomerRepository(db),
        authorization,
        db,
    )
