from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

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
from app.modules.activities.application.bulk_delete_activities import (
    BulkDeleteActivitiesUseCase,
)
from app.modules.activities.application.create_activity import CreateActivityUseCase
from app.modules.activities.application.delete_activity import DeleteActivityUseCase
from app.modules.activities.application.get_activity import GetActivityUseCase
from app.modules.activities.application.list_activities import ListActivitiesUseCase
from app.modules.activities.application.list_activities_by_customer import (
    ListActivitiesByCustomerUseCase,
)
from app.modules.activities.application.update_activity import UpdateActivityUseCase
from app.modules.activities.infrastructure.repositories.activity_repository import (
    SqlAlchemyActivityRepository,
)
from app.modules.contacts.infrastructure.repositories.contact_repository import (
    SqlAlchemyContactRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.activities.read"


def get_activity_repository(db: Session = Depends(get_db)) -> SqlAlchemyActivityRepository:
    return SqlAlchemyActivityRepository(db)


def get_contact_repository_for_activities(
    db: Session = Depends(get_db),
) -> SqlAlchemyContactRepository:
    return SqlAlchemyContactRepository(db)


def get_customer_repository_for_activities(
    db: Session = Depends(get_db),
) -> SqlAlchemyCustomerRepository:
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


def get_create_activity_use_case(
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository_for_activities),
    contact_repository: SqlAlchemyContactRepository = Depends(get_contact_repository_for_activities),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateActivityUseCase:
    return CreateActivityUseCase(
        activity_repository, customer_repository, contact_repository, authorization, audit
    )


def get_get_activity_use_case(
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository_for_activities),
    contact_repository: SqlAlchemyContactRepository = Depends(get_contact_repository_for_activities),
    db: Session = Depends(get_db),
) -> GetActivityUseCase:
    return GetActivityUseCase(
        activity_repository, customer_repository, contact_repository, db
    )


def get_list_activities_use_case(
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository_for_activities),
    contact_repository: SqlAlchemyContactRepository = Depends(get_contact_repository_for_activities),
    db: Session = Depends(get_db),
) -> ListActivitiesUseCase:
    return ListActivitiesUseCase(
        activity_repository, customer_repository, contact_repository, db
    )


def get_list_activities_by_customer_use_case(
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository_for_activities),
    contact_repository: SqlAlchemyContactRepository = Depends(get_contact_repository_for_activities),
) -> ListActivitiesByCustomerUseCase:
    return ListActivitiesByCustomerUseCase(
        activity_repository, customer_repository, contact_repository
    )


def get_update_activity_use_case(
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    contact_repository: SqlAlchemyContactRepository = Depends(get_contact_repository_for_activities),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateActivityUseCase:
    return UpdateActivityUseCase(activity_repository, contact_repository, authorization, audit)


def get_delete_activity_use_case(
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> DeleteActivityUseCase:
    return DeleteActivityUseCase(activity_repository, authorization, audit)


def get_bulk_delete_activities_use_case(
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> BulkDeleteActivitiesUseCase:
    return BulkDeleteActivitiesUseCase(activity_repository, authorization, audit)
