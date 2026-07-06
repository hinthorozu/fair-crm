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
from app.modules.todos.application.create_todo_outcome import CreateTodoOutcomeUseCase
from app.modules.todos.application.deactivate_todo_outcome import DeactivateTodoOutcomeUseCase
from app.modules.todos.application.ensure_default_outcomes import EnsureDefaultOutcomesUseCase
from app.modules.todos.application.get_todo_outcome import GetTodoOutcomeUseCase
from app.modules.todos.application.list_todo_outcomes import ListTodoOutcomesUseCase
from app.modules.todos.application.update_todo_outcome import UpdateTodoOutcomeUseCase
from app.modules.todos.infrastructure.repositories.outcome_definition_repository import (
    SqlAlchemyTodoOutcomeDefinitionRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.todos.outcomes.read"
PERMISSION_CREATE = "fair_crm.todos.outcomes.create"
PERMISSION_UPDATE = "fair_crm.todos.outcomes.update"
PERMISSION_DEACTIVATE = "fair_crm.todos.outcomes.deactivate"


def get_outcome_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyTodoOutcomeDefinitionRepository:
    return SqlAlchemyTodoOutcomeDefinitionRepository(db)


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


def require_outcome_read_permission(
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


def get_ensure_default_outcomes_use_case(
    repository: SqlAlchemyTodoOutcomeDefinitionRepository = Depends(get_outcome_repository),
) -> EnsureDefaultOutcomesUseCase:
    return EnsureDefaultOutcomesUseCase(repository)


def get_list_todo_outcomes_use_case(
    repository: SqlAlchemyTodoOutcomeDefinitionRepository = Depends(get_outcome_repository),
    ensure_defaults: EnsureDefaultOutcomesUseCase = Depends(get_ensure_default_outcomes_use_case),
) -> ListTodoOutcomesUseCase:
    return ListTodoOutcomesUseCase(repository, ensure_defaults)


def get_get_todo_outcome_use_case(
    repository: SqlAlchemyTodoOutcomeDefinitionRepository = Depends(get_outcome_repository),
) -> GetTodoOutcomeUseCase:
    return GetTodoOutcomeUseCase(repository)


def get_create_todo_outcome_use_case(
    repository: SqlAlchemyTodoOutcomeDefinitionRepository = Depends(get_outcome_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateTodoOutcomeUseCase:
    return CreateTodoOutcomeUseCase(repository, authorization, audit)


def get_update_todo_outcome_use_case(
    repository: SqlAlchemyTodoOutcomeDefinitionRepository = Depends(get_outcome_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateTodoOutcomeUseCase:
    return UpdateTodoOutcomeUseCase(repository, authorization, audit)


def get_deactivate_todo_outcome_use_case(
    repository: SqlAlchemyTodoOutcomeDefinitionRepository = Depends(get_outcome_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> DeactivateTodoOutcomeUseCase:
    return DeactivateTodoOutcomeUseCase(repository, authorization, audit)
