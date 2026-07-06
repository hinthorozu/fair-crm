from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.todos.api.dependencies import require_read_permission
from app.modules.todos.api.worklist_dependencies import (
    get_list_todo_worklist_use_case,
    get_todo_worklist_progress_use_case,
)
from app.modules.todos.api.worklist_schemas import (
    ErrorResponse,
    TodoWorklistListResponse,
    TodoWorklistProgressResponse,
    TodoWorklistRowResponse,
    WorklistFilterField,
)
from app.modules.todos.application.get_todo_worklist_progress import GetTodoWorklistProgressUseCase
from app.modules.todos.application.list_todo_worklist import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
    ListTodoWorklistUseCase,
)
from app.modules.todos.application.worklist_commands import (
    GetTodoWorklistProgressQuery,
    ListTodoWorklistQuery,
)
from app.modules.todos.domain.exceptions import TodoMissingSourceFairError, TodoNotFoundError
from app.modules.todos.domain.worklist_value_objects import WorklistFilter

router = APIRouter(prefix="/todos/{todo_id}/worklist", tags=["todo-worklist"])


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
