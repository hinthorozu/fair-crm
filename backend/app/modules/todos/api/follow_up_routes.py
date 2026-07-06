from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AliasChoices

from app.api.dependencies.list_query import parse_list_query, resolve_page_size_from_request
from app.api.list_helpers import standard_list_from_result
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.todos.api.follow_up_schemas import (
    ErrorResponse,
    FollowUpFilterField,
    FollowUpListResponse,
    FollowUpRowResponse,
)
from app.modules.todos.api.worklist_dependencies import (
    get_list_follow_ups_use_case,
    require_read_permission,
)
from app.modules.todos.application.list_follow_ups import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
    ListFollowUpsUseCase,
)
from app.modules.todos.application.worklist_commands import ListFollowUpsQuery
from app.modules.todos.domain.worklist_value_objects import FollowUpFilter

router = APIRouter(prefix="/follow-ups", tags=["follow-ups"])


def _parse_follow_up_filter(value: FollowUpFilterField | None) -> FollowUpFilter:
    if value is None:
        return FollowUpFilter.BUGUN
    return FollowUpFilter(value)


def _to_row_response(result) -> FollowUpRowResponse:
    return FollowUpRowResponse.model_validate(asdict(result))


@router.get(
    "",
    response_model=FollowUpListResponse,
    responses={
        403: {"model": ErrorResponse},
    },
)
def list_follow_ups(
    request: Request,
    follow_up_filter: FollowUpFilterField | None = Query(
        default="bugun",
        alias="filter",
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
    use_case: ListFollowUpsUseCase = Depends(get_list_follow_ups_use_case),
) -> FollowUpListResponse:
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
        ListFollowUpsQuery(
            organization_id=auth.organization_id,
            follow_up_filter=_parse_follow_up_filter(follow_up_filter),
            search=list_query.search,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    )

    filters: dict = {"filter": follow_up_filter or "bugun"}
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
