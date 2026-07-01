"""Helpers to build standard list API responses from use-case results."""

from __future__ import annotations

from typing import Any

from app.api.schemas.list_response import StandardListResponse, build_list_response
from app.core.pagination import SortDirection


class ListResultProtocol:
    items: list
    page: int
    page_size: int
    total: int
    total_pages: int


def standard_list_from_result(
    result: ListResultProtocol,
    *,
    sort_field: str,
    sort_direction: SortDirection,
    filters: dict[str, Any] | None = None,
) -> StandardListResponse:
    return build_list_response(
        list(result.items),
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        sort_field=sort_field,
        sort_direction=sort_direction,
        filters=filters,
    )
