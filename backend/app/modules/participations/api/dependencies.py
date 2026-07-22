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
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.participations.application.create_participation import CreateParticipationUseCase
from app.modules.participations.application.delete_participation import DeleteParticipationUseCase
from app.modules.participations.application.get_participation import GetParticipationUseCase
from app.modules.participations.application.list_by_customer import ListParticipationsByCustomerUseCase
from app.modules.participations.application.list_by_fair import ListParticipantsByFairUseCase
from app.modules.participations.application.update_participation import UpdateParticipationUseCase
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.participations.read"


def get_participation_repository(db: Session = Depends(get_db)) -> SqlAlchemyParticipationRepository:
    return SqlAlchemyParticipationRepository(db)


def get_customer_repository(db: Session = Depends(get_db)) -> SqlAlchemyCustomerRepository:
    return SqlAlchemyCustomerRepository(db)


def get_fair_repository(db: Session = Depends(get_db)) -> SqlAlchemyFairRepository:
    return SqlAlchemyFairRepository(db)


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
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
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


def get_create_participation_use_case(
    participation_repository: SqlAlchemyParticipationRepository = Depends(get_participation_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
    fair_repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateParticipationUseCase:
    return CreateParticipationUseCase(
        participation_repository,
        customer_repository,
        fair_repository,
        authorization,
        audit,
    )


def get_get_participation_use_case(
    repository: SqlAlchemyParticipationRepository = Depends(get_participation_repository),
) -> GetParticipationUseCase:
    return GetParticipationUseCase(repository)


def get_update_participation_use_case(
    participation_repository: SqlAlchemyParticipationRepository = Depends(get_participation_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateParticipationUseCase:
    return UpdateParticipationUseCase(participation_repository, authorization, audit)


def get_delete_participation_use_case(
    participation_repository: SqlAlchemyParticipationRepository = Depends(get_participation_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> DeleteParticipationUseCase:
    return DeleteParticipationUseCase(participation_repository, authorization, audit)


def get_list_by_customer_use_case(
    participation_repository: SqlAlchemyParticipationRepository = Depends(get_participation_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
) -> ListParticipationsByCustomerUseCase:
    return ListParticipationsByCustomerUseCase(participation_repository, customer_repository)


def get_list_by_fair_use_case(
    participation_repository: SqlAlchemyParticipationRepository = Depends(get_participation_repository),
    fair_repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
) -> ListParticipantsByFairUseCase:
    return ListParticipantsByFairUseCase(participation_repository, fair_repository)
