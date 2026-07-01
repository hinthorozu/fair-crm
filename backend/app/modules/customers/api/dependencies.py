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
from app.modules.customers.application.archive_customer import ArchiveCustomerUseCase
from app.modules.customers.application.create_customer import CreateCustomerUseCase
from app.modules.customers.application.get_customer import GetCustomerUseCase
from app.modules.customers.application.list_customers import ListCustomersUseCase
from app.modules.customers.application.restore_customer import RestoreCustomerUseCase
from app.modules.customers.application.update_customer import UpdateCustomerUseCase
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.customers.read"


def get_customer_repository(db: Session = Depends(get_db)) -> SqlAlchemyCustomerRepository:
    return SqlAlchemyCustomerRepository(db)


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


def get_create_customer_use_case(
    repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateCustomerUseCase:
    return CreateCustomerUseCase(repository, authorization, audit)


def get_get_customer_use_case(
    repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
) -> GetCustomerUseCase:
    return GetCustomerUseCase(repository)


def get_list_customers_use_case(
    repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
) -> ListCustomersUseCase:
    return ListCustomersUseCase(repository)


def get_update_customer_use_case(
    repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateCustomerUseCase:
    return UpdateCustomerUseCase(repository, authorization, audit)


def get_archive_customer_use_case(
    repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> ArchiveCustomerUseCase:
    return ArchiveCustomerUseCase(repository, authorization, audit)


def get_restore_customer_use_case(
    repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> RestoreCustomerUseCase:
    return RestoreCustomerUseCase(repository, authorization, audit)
