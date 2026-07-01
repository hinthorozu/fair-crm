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
from app.modules.contacts.application.create_contact import CreateContactUseCase
from app.modules.contacts.application.delete_contact import DeleteContactUseCase
from app.modules.contacts.application.get_contact import GetContactUseCase
from app.modules.contacts.application.list_contacts_by_customer import ListContactsByCustomerUseCase
from app.modules.contacts.application.update_contact import UpdateContactUseCase
from app.modules.contacts.infrastructure.repositories.contact_repository import (
    SqlAlchemyContactRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.contacts.read"


def get_contact_repository(db: Session = Depends(get_db)) -> SqlAlchemyContactRepository:
    return SqlAlchemyContactRepository(db)


def get_customer_repository_for_contacts(db: Session = Depends(get_db)) -> SqlAlchemyCustomerRepository:
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


def get_create_contact_use_case(
    contact_repository: SqlAlchemyContactRepository = Depends(get_contact_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository_for_contacts),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateContactUseCase:
    return CreateContactUseCase(contact_repository, customer_repository, authorization, audit)


def get_get_contact_use_case(
    repository: SqlAlchemyContactRepository = Depends(get_contact_repository),
) -> GetContactUseCase:
    return GetContactUseCase(repository)


def get_list_contacts_by_customer_use_case(
    contact_repository: SqlAlchemyContactRepository = Depends(get_contact_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository_for_contacts),
) -> ListContactsByCustomerUseCase:
    return ListContactsByCustomerUseCase(contact_repository, customer_repository)


def get_update_contact_use_case(
    repository: SqlAlchemyContactRepository = Depends(get_contact_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateContactUseCase:
    return UpdateContactUseCase(repository, authorization, audit)


def get_delete_contact_use_case(
    repository: SqlAlchemyContactRepository = Depends(get_contact_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> DeleteContactUseCase:
    return DeleteContactUseCase(repository, authorization, audit)
