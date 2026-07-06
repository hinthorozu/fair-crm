from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled
from app.modules.activities.application.list_activities_by_customer import (
    ListActivitiesByCustomerUseCase,
)
from app.modules.activities.infrastructure.repositories.activity_repository import (
    SqlAlchemyActivityRepository,
)
from app.modules.contacts.infrastructure.repositories.contact_repository import (
    SqlAlchemyContactRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.modules.todos.api.dependencies import (
    get_auth_context,
    get_authorization_adapter,
    require_read_permission,
)
from app.modules.todos.api.outcome_dependencies import (
    get_ensure_default_outcomes_use_case,
    get_list_todo_outcomes_use_case,
)
from app.modules.todos.application.get_todo_worklist_modal_context import GetTodoWorklistModalContextUseCase
from app.modules.todos.application.get_todo_worklist_progress import GetTodoWorklistProgressUseCase
from app.modules.todos.application.list_follow_ups import ListFollowUpsUseCase
from app.modules.todos.application.list_todo_worklist import ListTodoWorklistUseCase
from app.modules.todos.application.record_todo_worklist_activity import RecordTodoWorklistActivityUseCase
from app.modules.todos.infrastructure.repositories.outcome_definition_repository import (
    SqlAlchemyTodoOutcomeDefinitionRepository,
)
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository
from app.modules.todos.infrastructure.repositories.worklist_query_repository import (
    SqlAlchemyTodoWorklistQueryRepository,
)
from app.modules.todos.infrastructure.repositories.worklist_state_repository import (
    SqlAlchemyTodoWorklistStateRepository,
)

bearer_scheme = HTTPBearer(auto_error=False)
PERMISSION_CREATE = "fair_crm.todos.create"


def get_todo_repository(db: Session = Depends(get_db)) -> SqlAlchemyTodoRepository:
    return SqlAlchemyTodoRepository(db)


def get_worklist_query_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyTodoWorklistQueryRepository:
    return SqlAlchemyTodoWorklistQueryRepository(db)


def get_worklist_state_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyTodoWorklistStateRepository:
    return SqlAlchemyTodoWorklistStateRepository(db)


def get_outcome_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyTodoOutcomeDefinitionRepository:
    return SqlAlchemyTodoOutcomeDefinitionRepository(db)


def get_activity_repository(db: Session = Depends(get_db)) -> SqlAlchemyActivityRepository:
    return SqlAlchemyActivityRepository(db)


def get_participation_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyParticipationRepository:
    return SqlAlchemyParticipationRepository(db)


def get_list_todo_worklist_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    worklist_query_repository: SqlAlchemyTodoWorklistQueryRepository = Depends(
        get_worklist_query_repository
    ),
) -> ListTodoWorklistUseCase:
    return ListTodoWorklistUseCase(todo_repository, worklist_query_repository)


def get_list_follow_ups_use_case(
    worklist_query_repository: SqlAlchemyTodoWorklistQueryRepository = Depends(
        get_worklist_query_repository
    ),
) -> ListFollowUpsUseCase:
    return ListFollowUpsUseCase(worklist_query_repository)


def get_todo_worklist_progress_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    worklist_query_repository: SqlAlchemyTodoWorklistQueryRepository = Depends(
        get_worklist_query_repository
    ),
) -> GetTodoWorklistProgressUseCase:
    return GetTodoWorklistProgressUseCase(todo_repository, worklist_query_repository)


def get_list_activities_by_customer_use_case(
    db: Session = Depends(get_db),
) -> ListActivitiesByCustomerUseCase:
    return ListActivitiesByCustomerUseCase(
        SqlAlchemyActivityRepository(db),
        SqlAlchemyCustomerRepository(db),
        SqlAlchemyContactRepository(db),
    )


def get_record_todo_worklist_activity_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    outcome_repository: SqlAlchemyTodoOutcomeDefinitionRepository = Depends(get_outcome_repository),
    worklist_state_repository: SqlAlchemyTodoWorklistStateRepository = Depends(
        get_worklist_state_repository
    ),
    worklist_query_repository: SqlAlchemyTodoWorklistQueryRepository = Depends(
        get_worklist_query_repository
    ),
    activity_repository: SqlAlchemyActivityRepository = Depends(get_activity_repository),
    participation_repository: SqlAlchemyParticipationRepository = Depends(
        get_participation_repository
    ),
    authorization=Depends(get_authorization_adapter),
) -> RecordTodoWorklistActivityUseCase:
    return RecordTodoWorklistActivityUseCase(
        todo_repository,
        outcome_repository,
        worklist_state_repository,
        worklist_query_repository,
        activity_repository,
        participation_repository,
        authorization,
    )


def get_todo_worklist_modal_context_use_case(
    todo_repository: SqlAlchemyTodoRepository = Depends(get_todo_repository),
    worklist_query_repository: SqlAlchemyTodoWorklistQueryRepository = Depends(
        get_worklist_query_repository
    ),
    list_outcomes=Depends(get_list_todo_outcomes_use_case),
    ensure_defaults=Depends(get_ensure_default_outcomes_use_case),
    list_activities: ListActivitiesByCustomerUseCase = Depends(
        get_list_activities_by_customer_use_case
    ),
) -> GetTodoWorklistModalContextUseCase:
    return GetTodoWorklistModalContextUseCase(
        todo_repository,
        worklist_query_repository,
        list_outcomes,
        ensure_defaults,
        list_activities,
    )


def require_create_permission(
    auth: AuthContext = Depends(get_auth_context),
    authorization=Depends(get_authorization_adapter),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_CREATE,
        access_token=credentials.credentials,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return auth


def access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
