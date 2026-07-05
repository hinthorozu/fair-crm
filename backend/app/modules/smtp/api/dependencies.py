from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuditAdapter, HttpAuthorizationAdapter
from app.integrations.kyrox_core.dev_bypass import (
    AllowAllAuthorizationAdapter,
    NoOpAuditAdapter,
    dev_bypass_enabled,
    resolve_auth_context,
)
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.smtp.application.create_smtp_account import CreateSmtpAccountUseCase
from app.modules.smtp.application.delete_smtp_account import DeleteSmtpAccountUseCase
from app.modules.smtp.application.get_smtp_account import GetSmtpAccountUseCase
from app.modules.smtp.application.list_smtp_accounts import ListSmtpAccountsUseCase
from app.modules.smtp.application.set_default_smtp_account import SetDefaultSmtpAccountUseCase
from app.modules.smtp.application.send_test_smtp_mail import SendTestSmtpMailUseCase
from app.modules.smtp.application.update_smtp_account import UpdateSmtpAccountUseCase
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import (
    SqlAlchemySmtpAccountRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.smtp.read"


def get_smtp_account_repository(db: Session = Depends(get_db)) -> SqlAlchemySmtpAccountRepository:
    return SqlAlchemySmtpAccountRepository(db)


def get_authorization_adapter() -> AuthorizationPort:
    if dev_bypass_enabled():
        return AllowAllAuthorizationAdapter()
    return HttpAuthorizationAdapter()


def get_audit_adapter() -> HttpAuditAdapter | NoOpAuditAdapter:
    if dev_bypass_enabled():
        return NoOpAuditAdapter()
    return HttpAuditAdapter()


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


def get_create_smtp_account_use_case(
    repository: SqlAlchemySmtpAccountRepository = Depends(get_smtp_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateSmtpAccountUseCase:
    return CreateSmtpAccountUseCase(repository, authorization, audit)


def get_update_smtp_account_use_case(
    repository: SqlAlchemySmtpAccountRepository = Depends(get_smtp_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateSmtpAccountUseCase:
    return UpdateSmtpAccountUseCase(repository, authorization, audit)


def get_get_smtp_account_use_case(
    repository: SqlAlchemySmtpAccountRepository = Depends(get_smtp_account_repository),
) -> GetSmtpAccountUseCase:
    return GetSmtpAccountUseCase(repository)


def get_list_smtp_accounts_use_case(
    repository: SqlAlchemySmtpAccountRepository = Depends(get_smtp_account_repository),
) -> ListSmtpAccountsUseCase:
    return ListSmtpAccountsUseCase(repository)


def get_set_default_smtp_account_use_case(
    repository: SqlAlchemySmtpAccountRepository = Depends(get_smtp_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> SetDefaultSmtpAccountUseCase:
    return SetDefaultSmtpAccountUseCase(repository, authorization, audit)


def get_delete_smtp_account_use_case(
    repository: SqlAlchemySmtpAccountRepository = Depends(get_smtp_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> DeleteSmtpAccountUseCase:
    return DeleteSmtpAccountUseCase(repository, authorization, audit)


def get_send_test_smtp_mail_use_case(
    repository: SqlAlchemySmtpAccountRepository = Depends(get_smtp_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> SendTestSmtpMailUseCase:
    return SendTestSmtpMailUseCase(repository, authorization, audit)
