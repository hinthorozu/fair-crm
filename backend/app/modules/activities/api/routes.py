from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.activities.api.dependencies import (
    get_auth_context,
    get_create_activity_use_case,
    get_delete_activity_use_case,
    get_get_activity_use_case,
    get_list_activities_by_customer_use_case,
    get_update_activity_use_case,
    require_read_permission,
)
from app.modules.activities.api.schemas import (
    ActivityListResponse,
    ActivityResponse,
    CreateActivityRequest,
    ErrorResponse,
    UpdateActivityRequest,
)
from app.modules.activities.application.commands import (
    CreateActivityCommand,
    DeleteActivityCommand,
    GetActivityQuery,
    ListActivitiesByCustomerQuery,
    UpdateActivityCommand,
)
from app.modules.activities.application.create_activity import CreateActivityUseCase
from app.modules.activities.application.delete_activity import DeleteActivityUseCase
from app.modules.activities.application.get_activity import GetActivityUseCase
from app.modules.activities.application.list_activities_by_customer import (
    ListActivitiesByCustomerUseCase,
)
from app.modules.activities.application.update_activity import UpdateActivityUseCase
from app.modules.activities.domain.exceptions import (
    ActivityAlreadyDeletedError,
    ActivityNotFoundError,
    ContactCustomerMismatchError,
    ContactNotFoundForActivityError,
    CustomerArchivedForActivityError,
    CustomerNotFoundForActivityError,
    InvalidActivitySourceError,
    InvalidActivityStatusError,
    InvalidActivitySubjectError,
    InvalidActivityTypeError,
)

router = APIRouter(prefix="/activities", tags=["activities"])
customer_activities_router = APIRouter(
    prefix="/customers/{customer_id}/activities", tags=["activities"]
)
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> ActivityResponse:
    return ActivityResponse.model_validate(result.__dict__)


@customer_activities_router.get(
    "",
    response_model=ActivityListResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_activities_by_customer(
    customer_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="activity_date"),
    sort_dir: str = Query(default="desc", pattern="^(?i)(asc|desc)$"),
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListActivitiesByCustomerUseCase = Depends(get_list_activities_by_customer_use_case),
) -> ActivityListResponse:
    try:
        result = use_case.execute(
            ListActivitiesByCustomerQuery(
                organization_id=auth.organization_id,
                customer_id=customer_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_dir=sort_dir,
            )
        )
    except CustomerNotFoundForActivityError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ActivityListResponse(
        items=[_to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.post(
    "",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def create_activity(
    body: CreateActivityRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateActivityUseCase = Depends(get_create_activity_use_case),
) -> ActivityResponse:
    try:
        result = use_case.execute(
            CreateActivityCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                customer_id=body.customer_id,
                contact_id=body.contact_id,
                activity_type=body.type,
                subject=body.subject,
                description=body.description,
                activity_date=body.activity_date,
                follow_up_date=body.follow_up_date,
                status=body.status,
                source=body.source,
                is_active=body.is_active,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CustomerNotFoundForActivityError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CustomerArchivedForActivityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ContactNotFoundForActivityError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ContactCustomerMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActivitySubjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActivityTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActivityStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActivitySourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "/{activity_id}",
    response_model=ActivityResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_activity(
    activity_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetActivityUseCase = Depends(get_get_activity_use_case),
) -> ActivityResponse:
    try:
        result = use_case.execute(
            GetActivityQuery(
                organization_id=auth.organization_id,
                activity_id=activity_id,
            )
        )
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.patch(
    "/{activity_id}",
    response_model=ActivityResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def update_activity(
    activity_id: UUID,
    body: UpdateActivityRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateActivityUseCase = Depends(get_update_activity_use_case),
) -> ActivityResponse:
    data = body.model_dump(exclude_unset=True)
    try:
        result = use_case.execute(
            UpdateActivityCommand(
                organization_id=auth.organization_id,
                activity_id=activity_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                contact_id=data.get("contact_id"),
                activity_type=data.get("type"),
                subject=data.get("subject"),
                description=data.get("description"),
                activity_date=data.get("activity_date"),
                follow_up_date=data.get("follow_up_date"),
                status=data.get("status"),
                source=data.get("source"),
                is_active=data.get("is_active"),
                set_contact_id="contact_id" in data,
                set_description="description" in data,
                set_follow_up_date="follow_up_date" in data,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ActivityAlreadyDeletedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ContactNotFoundForActivityError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ContactCustomerMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActivitySubjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActivityTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActivityStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActivitySourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.delete(
    "/{activity_id}",
    response_model=ActivityResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def delete_activity(
    activity_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteActivityUseCase = Depends(get_delete_activity_use_case),
) -> ActivityResponse:
    try:
        result = use_case.execute(
            DeleteActivityCommand(
                organization_id=auth.organization_id,
                activity_id=activity_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)
