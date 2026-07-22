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
from app.modules.activities.infrastructure.repositories.activity_repository import (
    SqlAlchemyActivityRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.todos.application.archive_todo import ArchiveTodoUseCase
from app.modules.todos.application.complete_todo import CompleteTodoUseCase
from app.modules.todos.application.create_todo import CreateTodoUseCase
from app.modules.todos.application.delete_todo import DeleteTodoUseCase
from app.modules.todos.application.get_todo import GetTodoUseCase
from app.modules.todos.application.list_todos import ListTodosUseCase
from app.modules.todos.application.update_todo import UpdateTodoUseCase
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository
from app.modules.todos.infrastructure.repositories.worklist_state_repository import (
    SqlAlchemyTodoWorklistStateRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.todos.read"


def get_todo_repository(db: Session = Depends(get_db)) -> SqlAlchemyTodoRepository:
    return SqlAlchemyTodoRepository(db)


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


def get_fair_repository(db: Session = Depends(get_db)) -> SqlAlchemyFairRepository:
    return SqlAlchemyFairRepository(db)


def get_customer_repository(db: Session = Depends(get_db)) -> SqlAlchemyCustomerRepository:
    return SqlAlchemyCustomerRepository(db)


def get_worklist_state_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyTodoWorklistStateRepository:
    return SqlAlchemyTodoWorklistStateRepository(db)


def get_create_todo_use_case(
    repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    fair_repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateTodoUseCase:
    return CreateTodoUseCase(
        repository,
        fair_repository,
        customer_repository,
        authorization,
        audit,
    )


def get_get_todo_use_case(
    repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
) -> GetTodoUseCase:
    return GetTodoUseCase(repository)


def get_list_todos_use_case(
    repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
) -> ListTodosUseCase:
    return ListTodosUseCase(repository)


def get_update_todo_use_case(
    repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    fair_repository: SqlAlchemyFairRepository = Depends(get_fair_repository),
    customer_repository: SqlAlchemyCustomerRepository = Depends(get_customer_repository),
    worklist_state_repository: SqlAlchemyTodoWorklistStateRepository = Depends(
        get_worklist_state_repository
    ),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateTodoUseCase:
    return UpdateTodoUseCase(
        repository,
        fair_repository,
        customer_repository,
        worklist_state_repository,
        authorization,
        audit,
    )


def get_activity_repository(db: Session = Depends(get_db)) -> SqlAlchemyActivityRepository:
    return SqlAlchemyActivityRepository(db)


def get_complete_todo_use_case(
    repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CompleteTodoUseCase:
    return CompleteTodoUseCase(repository, activity_repository, authorization, audit)


def get_archive_todo_use_case(
    repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> ArchiveTodoUseCase:
    return ArchiveTodoUseCase(repository, authorization, audit)


def get_delete_todo_use_case(
    repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> DeleteTodoUseCase:
    return DeleteTodoUseCase(repository, authorization, audit)
