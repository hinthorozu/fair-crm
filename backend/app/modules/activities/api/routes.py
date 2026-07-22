from datetime import datetime, time, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.modules.activities.application.list_activities import (
    ALLOWED_SORT_FIELDS as LIST_ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION as LIST_DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD as LIST_DEFAULT_SORT_FIELD,
)
from app.modules.activities.application.list_activities_by_customer import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
)

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.activities.api.dependencies import (
    get_auth_context,
    get_bulk_delete_activities_use_case,
    get_create_activity_use_case,
    get_delete_activity_use_case,
    get_get_activity_use_case,
    get_list_activities_by_customer_use_case,
    get_list_activities_use_case,
    get_update_activity_use_case,
    require_read_permission,
)
from app.modules.activities.api.schemas import (
    ActivityListResponse,
    ActivityResponse,
    BulkDeleteActivitiesRequest,
    BulkDeleteActivitiesResponse,
    CreateActivityRequest,
    ErrorResponse,
    UpdateActivityRequest,
)
from app.modules.activities.application.bulk_delete_activities import (
    BulkDeleteActivitiesUseCase,
)
from app.modules.activities.application.commands import (
    BulkDeleteActivitiesCommand,
    CreateActivityCommand,
    DeleteActivityCommand,
    GetActivityQuery,
    ListActivitiesByCustomerQuery,
    ListActivitiesQuery,
    UpdateActivityCommand,
)
from app.modules.activities.application.create_activity import CreateActivityUseCase
from app.modules.activities.application.delete_activity import DeleteActivityUseCase
from app.modules.activities.application.get_activity import GetActivityUseCase
from app.modules.activities.application.list_activities import ListActivitiesUseCase
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


def _parse_date_start(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_from"
        ) from exc
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


def _parse_date_end(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_to"
        ) from exc
    return datetime.combine(parsed, time.max, tzinfo=timezone.utc)


@customer_activities_router.get(
    "",
    response_model=ActivityListResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_activities_by_customer(
    request: Request,
    customer_id: UUID,
    activity_type: str | None = Query(default=None, alias="activityType"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: Annotated[
        int,
        Query(ge=1, le=100, validation_alias=AliasChoices("pageSize", "page_size")),
    ] = 25,
    sort: Annotated[
        str | None,
        Query(validation_alias=AliasChoices("sort_by", "sort")),
    ] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    direction: Annotated[
        str | None,
        Query(
            pattern="^(?i)(asc|desc)$",
            validation_alias=AliasChoices("sort_order", "sort_dir", "direction"),
        ),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListActivitiesByCustomerUseCase = Depends(get_list_activities_by_customer_use_case),
) -> ActivityListResponse:
    try:
        list_query = parse_list_query(
            page=page,
            page_size=resolve_page_size_from_request(request, page_size),
            search=search,
            sort=sort,
            sort_by=sort_by,
            direction=direction,
            sort_dir=sort_dir,
            default_sort=DEFAULT_SORT_FIELD,
            allowed_sort_fields=ALLOWED_SORT_FIELDS,
            default_direction=DEFAULT_SORT_DIRECTION,
        )
        result = use_case.execute(
            ListActivitiesByCustomerQuery(
                organization_id=auth.organization_id,
                customer_id=customer_id,
                search=list_query.search,
                activity_type=activity_type.strip() if activity_type and activity_type.strip() else None,
                page=list_query.page,
                page_size=list_query.page_size,
                sort_by=list_query.sort_by,
                sort_dir=list_query.sort_dir,
            )
        )
    except CustomerNotFoundForActivityError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filters: dict = {}
    if list_query.search:
        filters["search"] = list_query.search
    if activity_type and activity_type.strip():
        filters["activityType"] = activity_type.strip()

    return standard_list_from_result(
        result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters=filters,
    ).model_copy(
        update={"items": [_to_response(item) for item in result.items]},
    )


@router.get(
    "",
    response_model=ActivityListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_activities(
    request: Request,
    activity_type: str | None = Query(default=None, alias="activityType"),
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: UUID | None = Query(default=None, alias="customerId"),
    fair_id: UUID | None = Query(default=None, alias="fairId"),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: Annotated[
        int,
        Query(ge=1, le=100, validation_alias=AliasChoices("pageSize", "page_size")),
    ] = 25,
    sort: Annotated[
        str | None,
        Query(validation_alias=AliasChoices("sort_by", "sort")),
    ] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    direction: Annotated[
        str | None,
        Query(
            pattern="^(?i)(asc|desc)$",
            validation_alias=AliasChoices("sort_order", "sort_dir", "direction"),
        ),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListActivitiesUseCase = Depends(get_list_activities_use_case),
) -> ActivityListResponse:
    list_query = parse_list_query(
        page=page,
        page_size=resolve_page_size_from_request(request, page_size),
        search=search,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        default_sort=LIST_DEFAULT_SORT_FIELD,
        allowed_sort_fields=LIST_ALLOWED_SORT_FIELDS,
        default_direction=LIST_DEFAULT_SORT_DIRECTION,
    )
    result = use_case.execute(
        ListActivitiesQuery(
            organization_id=auth.organization_id,
            search=list_query.search,
            customer_id=customer_id,
            fair_id=fair_id,
            activity_type=activity_type.strip() if activity_type and activity_type.strip() else None,
            status=status_filter.strip() if status_filter and status_filter.strip() else None,
            date_from=_parse_date_start(date_from),
            date_to=_parse_date_end(date_to),
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    )

    filters: dict = {}
    if list_query.search:
        filters["search"] = list_query.search
    if activity_type and activity_type.strip():
        filters["activityType"] = activity_type.strip()
    if status_filter and status_filter.strip():
        filters["status"] = status_filter.strip()
    if customer_id is not None:
        filters["customerId"] = str(customer_id)
    if fair_id is not None:
        filters["fairId"] = str(fair_id)
    if date_from and date_from.strip():
        filters["dateFrom"] = date_from.strip()
    if date_to and date_to.strip():
        filters["dateTo"] = date_to.strip()

    return standard_list_from_result(
        result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters=filters,
    ).model_copy(
        update={"items": [_to_response(item) for item in result.items]},
    )


@router.post(
    "/bulk-delete",
    response_model=BulkDeleteActivitiesResponse,
    responses={403: {"model": ErrorResponse}},
)
def bulk_delete_activities(
    body: BulkDeleteActivitiesRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: BulkDeleteActivitiesUseCase = Depends(get_bulk_delete_activities_use_case),
) -> BulkDeleteActivitiesResponse:
    try:
        result = use_case.execute(
            BulkDeleteActivitiesCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                activity_ids=body.activity_ids,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return BulkDeleteActivitiesResponse(
        deleted_ids=result.deleted_ids,
        not_found_ids=result.not_found_ids,
        deleted_count=result.deleted_count,
        not_found_count=result.not_found_count,
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
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def delete_activity(
    activity_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeleteActivityUseCase = Depends(get_delete_activity_use_case),
) -> Response:
    try:
        use_case.execute(
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)
