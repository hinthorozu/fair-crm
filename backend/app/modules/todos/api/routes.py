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
from app.modules.todos.api.dependencies import (
    get_auth_context,
    get_create_todo_use_case,
    get_get_todo_use_case,
    get_list_todos_use_case,
    get_update_todo_use_case,
    require_read_permission,
)
from app.modules.todos.api.schemas import (
    CreateTodoRequest,
    ErrorResponse,
    TodoListResponse,
    TodoResponse,
    UpdateTodoRequest,
)
from app.modules.todos.application.commands import (
    CreateTodoCommand,
    GetTodoQuery,
    ListTodosQuery,
    UpdateTodoCommand,
)
from app.modules.todos.application.create_todo import CreateTodoUseCase
from app.modules.todos.application.get_todo import GetTodoUseCase
from app.modules.todos.application.list_todos import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
    ListTodosUseCase,
)
from app.modules.todos.application.update_todo import UpdateTodoUseCase
from app.modules.todos.domain.exceptions import (
    InvalidTodoCategoryError,
    InvalidTodoPriorityError,
    InvalidTodoStatusError,
    InvalidTodoTitleError,
    TodoNotFoundError,
)

router = APIRouter(prefix="/todos", tags=["todos"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_response(result) -> TodoResponse:
    return TodoResponse.model_validate(asdict(result))


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def create_todo(
    body: CreateTodoRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: CreateTodoUseCase = Depends(get_create_todo_use_case),
) -> TodoResponse:
    try:
        result = use_case.execute(
            CreateTodoCommand(
                organization_id=auth.organization_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                title=body.title,
                description=body.description,
                status=body.status,
                priority=body.priority,
                category=body.category,
                deadline=body.deadline,
                assignee_user_id=body.assignee_user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidTodoTitleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidTodoStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidTodoPriorityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidTodoCategoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.get(
    "",
    response_model=TodoListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_todos(
    request: Request,
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
    sort_order: Annotated[
        str | None,
        Query(pattern="^(?i)(asc|desc)$"),
    ] = None,
    direction: Annotated[
        str | None,
        Query(
            pattern="^(?i)(asc|desc)$",
            validation_alias=AliasChoices("sort_dir", "direction"),
            include_in_schema=False,
        ),
    ] = None,
    sort_dir: Annotated[
        str | None,
        Query(
            pattern="^(?i)(asc|desc)$",
            validation_alias=AliasChoices("sortDir", "sort_dir"),
            include_in_schema=False,
        ),
    ] = None,
    auth: AuthContext = Depends(require_read_permission),
    use_case: ListTodosUseCase = Depends(get_list_todos_use_case),
) -> TodoListResponse:
    resolved_page_size = resolve_page_size_from_request(request, page_size)
    list_query = parse_list_query(
        page=page,
        page_size=resolved_page_size,
        search=search,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order or request.query_params.get("sort_order"),
        default_sort=DEFAULT_SORT_FIELD,
        allowed_sort_fields=ALLOWED_SORT_FIELDS,
        default_direction=DEFAULT_SORT_DIRECTION,
    )
    result = use_case.execute(
        ListTodosQuery(
            organization_id=auth.organization_id,
            search=list_query.search,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    )
    filters: dict[str, str | None] = {"search": list_query.search}
    return standard_list_from_result(
        result,
        sort_field=list_query.sort_by,
        sort_direction=list_query.sort_dir,
        filters=filters,
    ).model_copy(
        update={"items": [_to_response(item) for item in result.items]},
    )


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_todo(
    todo_id: UUID,
    auth: AuthContext = Depends(require_read_permission),
    use_case: GetTodoUseCase = Depends(get_get_todo_use_case),
) -> TodoResponse:
    try:
        result = use_case.execute(
            GetTodoQuery(
                organization_id=auth.organization_id,
                todo_id=todo_id,
            )
        )
    except TodoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(result)


@router.patch(
    "/{todo_id}",
    response_model=TodoResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def update_todo(
    todo_id: UUID,
    body: UpdateTodoRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: UpdateTodoUseCase = Depends(get_update_todo_use_case),
) -> TodoResponse:
    data = body.model_dump(exclude_unset=True)
    try:
        result = use_case.execute(
            UpdateTodoCommand(
                organization_id=auth.organization_id,
                todo_id=todo_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                title=data.get("title"),
                description=data.get("description"),
                status=data.get("status"),
                priority=data.get("priority"),
                category=data.get("category"),
                deadline=data.get("deadline"),
                assignee_user_id=data.get("assignee_user_id"),
                set_description="description" in data,
                set_deadline="deadline" in data,
                set_assignee_user_id="assignee_user_id" in data,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TodoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTodoTitleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidTodoStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidTodoPriorityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidTodoCategoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)
