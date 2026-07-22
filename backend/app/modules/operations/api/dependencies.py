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
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.operations.application.cancel_operation import CancelOperationUseCase
from app.modules.operations.application.create_operation import CreateOperationUseCase
from app.modules.operations.application.get_operation import GetOperationUseCase
from app.modules.operations.application.get_wizard_metadata import GetWizardMetadataUseCase
from app.modules.operations.application.list_operation_runs import ListOperationRunsUseCase
from app.modules.operations.application.list_operations import ListOperationsUseCase
from app.modules.operations.application.retry_operation import RetryOperationUseCase
from app.modules.operations.application.start_operation import StartOperationUseCase
from app.modules.operations.domain.type_registry import default_operation_type_registry
from app.modules.operations.domain.handler_registry import InMemoryHandlerRegistry
from app.modules.operations.infrastructure.handlers.registry import (
    build_handler_registry,
    default_handler_registry,
)
from app.modules.operations.infrastructure.repositories.operation_repository import (
    SqlAlchemyOperationRepository,
)
from app.modules.operations.infrastructure.repositories.operation_run_repository import (
    SqlAlchemyOperationRunRepository,
)
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.operations.read"


def get_operation_repository(db: Session = Depends(get_db)) -> SqlAlchemyOperationRepository:
    return SqlAlchemyOperationRepository(db)


def get_operation_run_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyOperationRunRepository:
    return SqlAlchemyOperationRunRepository(db)


def get_fair_repository_for_operations(db: Session = Depends(get_db)) -> SqlAlchemyFairRepository:
    return SqlAlchemyFairRepository(db)


def get_customer_repository_for_operations(
    db: Session = Depends(get_db),
) -> SqlAlchemyCustomerRepository:
    return SqlAlchemyCustomerRepository(db)


def get_todo_repository_for_operations(db: Session = Depends(get_db)) -> SqlAlchemyTodoRepository:
    return SqlAlchemyTodoRepository(db)


def get_handler_registry(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository_for_operations),
    fair_repository: SqlAlchemyFairRepository = Depends(get_fair_repository_for_operations),
    customer_repository: SqlAlchemyCustomerRepository = Depends(
        get_customer_repository_for_operations
    ),
) -> InMemoryHandlerRegistry:
    return build_handler_registry(
        todo_repository=todo_repository,
        fair_repository=fair_repository,
        customer_repository=customer_repository,
    )


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        ) from exc


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


def get_start_operation_use_case(
    operation_repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
    run_repository: SqlAlchemyOperationRunRepository = Depends(get_operation_run_repository),
    handler_registry: InMemoryHandlerRegistry = Depends(get_handler_registry),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> StartOperationUseCase:
    return StartOperationUseCase(
        operation_repository,
        run_repository,
        handler_registry,
        authorization,
        audit,
    )


def get_create_operation_use_case(
    operation_repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
    fair_repository: SqlAlchemyFairRepository = Depends(get_fair_repository_for_operations),
    handler_registry: InMemoryHandlerRegistry = Depends(get_handler_registry),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
    start_use_case: StartOperationUseCase = Depends(get_start_operation_use_case),
) -> CreateOperationUseCase:
    return CreateOperationUseCase(
        operation_repository,
        default_operation_type_registry,
        handler_registry,
        authorization,
        audit,
        fair_repository=fair_repository,
        start_operation_use_case=start_use_case,
    )


def get_get_operation_use_case(
    operation_repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
    run_repository: SqlAlchemyOperationRunRepository = Depends(get_operation_run_repository),
    handler_registry: InMemoryHandlerRegistry = Depends(get_handler_registry),
) -> GetOperationUseCase:
    return GetOperationUseCase(
        operation_repository,
        run_repository,
        handler_registry,
    )


def get_list_operations_use_case(
    operation_repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
    handler_registry: InMemoryHandlerRegistry = Depends(get_handler_registry),
) -> ListOperationsUseCase:
    return ListOperationsUseCase(operation_repository, handler_registry)


def get_list_operation_runs_use_case(
    operation_repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
    run_repository: SqlAlchemyOperationRunRepository = Depends(get_operation_run_repository),
) -> ListOperationRunsUseCase:
    return ListOperationRunsUseCase(operation_repository, run_repository)


def get_cancel_operation_use_case(
    operation_repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
    run_repository: SqlAlchemyOperationRunRepository = Depends(get_operation_run_repository),
    handler_registry: InMemoryHandlerRegistry = Depends(get_handler_registry),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CancelOperationUseCase:
    return CancelOperationUseCase(
        operation_repository,
        run_repository,
        handler_registry,
        authorization,
        audit,
    )


def get_retry_operation_use_case(
    operation_repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
    run_repository: SqlAlchemyOperationRunRepository = Depends(get_operation_run_repository),
    handler_registry: InMemoryHandlerRegistry = Depends(get_handler_registry),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> RetryOperationUseCase:
    return RetryOperationUseCase(
        operation_repository,
        run_repository,
        handler_registry,
        authorization,
        audit,
    )


def get_wizard_metadata_use_case() -> GetWizardMetadataUseCase:
    return GetWizardMetadataUseCase(
        default_operation_type_registry,
        default_handler_registry,
    )
