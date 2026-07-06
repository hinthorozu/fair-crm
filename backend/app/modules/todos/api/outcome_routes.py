from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.todos.api.outcome_dependencies import (
    get_auth_context,
    get_create_todo_outcome_use_case,
    get_deactivate_todo_outcome_use_case,
    get_get_todo_outcome_use_case,
    get_list_todo_outcomes_use_case,
    get_update_todo_outcome_use_case,
    require_outcome_read_permission,
)
from app.modules.todos.api.outcome_schemas import (
    CreateTodoOutcomeRequest,
    ErrorResponse,
    OutcomeActiveFilterField,
    TodoOutcomeListResponse,
    TodoOutcomeResponse,
    UpdateTodoOutcomeRequest,
)
from app.modules.todos.application.create_todo_outcome import CreateTodoOutcomeUseCase
from app.modules.todos.application.deactivate_todo_outcome import DeactivateTodoOutcomeUseCase
from app.modules.todos.application.get_todo_outcome import GetTodoOutcomeUseCase
from app.modules.todos.application.list_todo_outcomes import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
    ListTodoOutcomesUseCase,
)
from app.modules.todos.application.outcome_commands import (
    CreateTodoOutcomeCommand,
    DeactivateTodoOutcomeCommand,
    GetTodoOutcomeQuery,
    ListTodoOutcomesQuery,
    UpdateTodoOutcomeCommand,
)
from app.modules.todos.application.update_todo_outcome import UpdateTodoOutcomeUseCase
from app.modules.todos.domain.exceptions import (
    DuplicateOutcomeCodeError,
    InvalidOutcomeCodeError,
    InvalidOutcomeNameError,
    InvalidOutcomePrimaryWorklistStatusError,
    OutcomeCodeImmutableError,
    TodoOutcomeDefinitionNotFoundError,
)

router = APIRouter(prefix="/todo-outcomes", tags=["todo-outcomes"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> TodoOutcomeResponse:
    return TodoOutcomeResponse.model_validate(asdict(result))


def _parse_is_active_filter(value: OutcomeActiveFilterField | None) -> bool | None:
    if value is None or value == "all":
        return None
    return value == "true"


@router.get(
    "",
    response_model=TodoOutcomeListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_todo_outcomes(
    request: Request,
    is_active: OutcomeActiveFilterField | None = Query(default="all"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: Annotated[
        int,
        Query(ge=1, le=100, validation_alias=AliasChoices("pageSize", "page_size")),
    ] = 100,
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
    auth: AuthContext = Depends(require_outcome_read_permission),
    use_case: ListTodoOutcomesUseCase = Depends(get_list_todo_outcomes_use_case),
) -> TodoOutcomeListResponse:
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
        ListTodoOutcomesQuery(
            organization_id=auth.organization_id,
            is_active=_parse_is_active_filter(is_active),
            search=list_query.search,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    )
    filters: dict = {"is_active": is_active or "all"}
    if list_query.search:
        filters["search"] = list_query.search
    return standard_list_from_result(
        result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters=filters,
    ).model_copy(
        update={"items": [_to_response(item) for item in result.items]},
    )


@router.post(
    "",
    response_model=TodoOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def create_todo_outcome(
    body: CreateTodoOutcomeRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateTodoOutcomeUseCase = Depends(get_create_todo_outcome_use_case),
) -> TodoOutcomeResponse:
    try:
        result = use_case.execute(
            CreateTodoOutcomeCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                name=body.name,
                code=body.code,
                primary_worklist_status=body.primary_worklist_status,
                description=body.description,
                sort_order=body.sort_order,
                requires_action=body.requires_action,
                marks_data_problem=body.marks_data_problem,
                is_active=body.is_active,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except DuplicateOutcomeCodeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (
        InvalidOutcomeCodeError,
        InvalidOutcomeNameError,
        InvalidOutcomePrimaryWorklistStatusError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "/{outcome_id}",
    response_model=TodoOutcomeResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_todo_outcome(
    outcome_id: UUID,
    auth: AuthContext = Depends(require_outcome_read_permission),
    use_case: GetTodoOutcomeUseCase = Depends(get_get_todo_outcome_use_case),
) -> TodoOutcomeResponse:
    try:
        result = use_case.execute(
            GetTodoOutcomeQuery(
                organization_id=auth.organization_id,
                outcome_id=outcome_id,
            )
        )
    except TodoOutcomeDefinitionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.patch(
    "/{outcome_id}",
    response_model=TodoOutcomeResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def update_todo_outcome(
    outcome_id: UUID,
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateTodoOutcomeUseCase = Depends(get_update_todo_outcome_use_case),
) -> TodoOutcomeResponse:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if "code" in payload:
        raise HTTPException(status_code=400, detail="Outcome code is immutable")

    body = UpdateTodoOutcomeRequest.model_validate(payload)
    raw = body.model_dump(exclude_unset=True)

    try:
        result = use_case.execute(
            UpdateTodoOutcomeCommand(
                organization_id=auth.organization_id,
                outcome_id=outcome_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                name=raw.get("name"),
                description=raw.get("description"),
                primary_worklist_status=raw.get("primary_worklist_status"),
                requires_action=raw.get("requires_action"),
                marks_data_problem=raw.get("marks_data_problem"),
                sort_order=raw.get("sort_order"),
                is_active=raw.get("is_active"),
                set_description="description" in raw,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TodoOutcomeDefinitionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        InvalidOutcomeNameError,
        InvalidOutcomePrimaryWorklistStatusError,
        OutcomeCodeImmutableError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.post(
    "/{outcome_id}/deactivate",
    response_model=TodoOutcomeResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def deactivate_todo_outcome(
    outcome_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: DeactivateTodoOutcomeUseCase = Depends(get_deactivate_todo_outcome_use_case),
) -> TodoOutcomeResponse:
    try:
        result = use_case.execute(
            DeactivateTodoOutcomeCommand(
                organization_id=auth.organization_id,
                outcome_id=outcome_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TodoOutcomeDefinitionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)
