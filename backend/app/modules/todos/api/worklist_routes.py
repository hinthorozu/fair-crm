from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.todos.api.worklist_activity_schemas import (
    RecordTodoWorklistActivityRequest,
    TodoWorklistActivityResponse,
    TodoWorklistModalContextResponse,
)
from app.modules.todos.api.worklist_dependencies import (
    access_token,
    get_list_todo_worklist_use_case,
    get_record_todo_worklist_activity_use_case,
    get_todo_worklist_modal_context_use_case,
    get_todo_worklist_progress_use_case,
    require_create_permission,
    require_read_permission,
)
from app.modules.todos.api.worklist_schemas import (
    ErrorResponse,
    TodoWorklistListResponse,
    TodoWorklistProgressResponse,
    TodoWorklistRowResponse,
    WorklistFilterField,
)
from app.modules.todos.application.get_todo_worklist_modal_context import GetTodoWorklistModalContextUseCase
from app.modules.todos.application.get_todo_worklist_progress import GetTodoWorklistProgressUseCase
from app.modules.todos.application.list_todo_worklist import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
    ListTodoWorklistUseCase,
)
from app.modules.todos.application.record_todo_worklist_activity import RecordTodoWorklistActivityUseCase
from app.modules.todos.application.worklist_commands import (
    GetTodoWorklistModalContextQuery,
    GetTodoWorklistProgressQuery,
    ListTodoWorklistQuery,
    RecordTodoWorklistActivityCommand,
)
from app.modules.todos.domain.exceptions import (
    InvalidWorklistNoteError,
    TodoMissingSourceFairError,
    TodoNotFoundError,
    TodoOutcomeDefinitionNotFoundError,
    TodoOutcomeInactiveError,
    WorklistCustomerNotInTodoError,
)
from app.modules.todos.domain.worklist_value_objects import WorklistFilter

router = APIRouter(prefix="/todos/{todo_id}/worklist", tags=["todo-worklist"])
bearer_scheme = HTTPBearer(auto_error=False)


def _to_row_response(result) -> TodoWorklistRowResponse:
    return TodoWorklistRowResponse.model_validate(asdict(result))


def _parse_worklist_filter(value: WorklistFilterField | None) -> WorklistFilter:
    if value is None:
        return WorklistFilter.YAPILMADI
    return WorklistFilter(value)


@router.get(
    "",
    response_model=TodoWorklistListResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def list_todo_worklist(
    todo_id: UUID,
    request: Request,
    worklist_filter: WorklistFilterField | None = Query(
        default="yapilmadi",
        alias="filter",
        validation_alias=AliasChoices("filter", "worklist_filter"),
    ),
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
    use_case: ListTodoWorklistUseCase = Depends(get_list_todo_worklist_use_case),
) -> TodoWorklistListResponse:
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
    try:
        result = use_case.execute(
            ListTodoWorklistQuery(
                organization_id=auth.organization_id,
                todo_id=todo_id,
                worklist_filter=_parse_worklist_filter(worklist_filter),
                search=list_query.search,
                page=list_query.page,
                page_size=list_query.page_size,
                sort_by=list_query.sort_by,
                sort_dir=list_query.sort_dir,
            )
        )
    except TodoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TodoMissingSourceFairError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filters: dict = {"filter": worklist_filter or "yapilmadi"}
    if list_query.search:
        filters["search"] = list_query.search
    return standard_list_from_result(
        result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters=filters,
    ).model_copy(
        update={"items": [_to_row_response(item) for item in result.items]},
    )


@router.get(
    "/progress",
    response_model=TodoWorklistProgressResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_todo_worklist_progress(
    todo_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetTodoWorklistProgressUseCase = Depends(get_todo_worklist_progress_use_case),
) -> TodoWorklistProgressResponse:
    try:
        result = use_case.execute(
            GetTodoWorklistProgressQuery(
                organization_id=auth.organization_id,
                todo_id=todo_id,
            )
        )
    except TodoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TodoMissingSourceFairError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TodoWorklistProgressResponse.model_validate(asdict(result))


@router.get(
    "/customers/{customer_id}/modal",
    response_model=TodoWorklistModalContextResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_todo_worklist_modal_context(
    todo_id: UUID,
    customer_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetTodoWorklistModalContextUseCase = Depends(get_todo_worklist_modal_context_use_case),
) -> TodoWorklistModalContextResponse:
    try:
        result = use_case.execute(
            GetTodoWorklistModalContextQuery(
                organization_id=auth.organization_id,
                todo_id=todo_id,
                customer_id=customer_id,
            )
        )
    except TodoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TodoMissingSourceFairError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorklistCustomerNotInTodoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = asdict(result)
    payload["outcomes"] = [asdict(item) for item in result.outcomes]
    payload["recent_activities"] = [asdict(item) for item in result.recent_activities]
    return TodoWorklistModalContextResponse.model_validate(payload)


@router.post(
    "/customers/{customer_id}/activities",
    response_model=TodoWorklistActivityResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def record_todo_worklist_activity(
    todo_id: UUID,
    customer_id: UUID,
    body: RecordTodoWorklistActivityRequest,
    auth: AuthContext = Depends(require_create_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: RecordTodoWorklistActivityUseCase = Depends(get_record_todo_worklist_activity_use_case),
) -> TodoWorklistActivityResponse:
    try:
        result = use_case.execute(
            RecordTodoWorklistActivityCommand(
                organization_id=auth.organization_id,
                access_token=access_token(credentials),
                user_id=auth.user_id,
                todo_id=todo_id,
                customer_id=customer_id,
                outcome_id=body.outcome_id,
                note=body.note,
                activity_type=body.activity_type,
                contact_id=body.contact_id,
                follow_up_at=body.follow_up_at,
                action_required=body.action_required,
                data_problem=body.data_problem,
                advance_to_next=body.advance_to_next,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TodoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TodoMissingSourceFairError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorklistCustomerNotInTodoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TodoOutcomeDefinitionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TodoOutcomeInactiveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidWorklistNoteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TodoWorklistActivityResponse(
        activity_id=result.activity_id,
        worklist_row=TodoWorklistRowResponse.model_validate(asdict(result.worklist_row)),
        progress=TodoWorklistProgressResponse.model_validate(asdict(result.progress)),
        next_customer_id=result.next_customer_id,
    )
