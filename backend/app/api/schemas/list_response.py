"""Standard paginated list response (ADR-015)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import PaginatedResult, SortDirection

T = TypeVar("T")


class ListPaginationInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100, serialization_alias="pageSize")
    total_items: int = Field(..., ge=0, serialization_alias="totalItems")
    total_pages: int = Field(..., ge=0, serialization_alias="totalPages")
    has_next: bool = Field(..., serialization_alias="hasNext")
    has_previous: bool = Field(..., serialization_alias="hasPrevious")


class ListSortingInfo(BaseModel):
    field: str
    direction: SortDirection


class StandardListResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    items: list[T]
    pagination: ListPaginationInfo
    sorting: ListSortingInfo
    filters: dict[str, Any] = Field(default_factory=dict)


def pagination_info_from_result(result: PaginatedResult) -> ListPaginationInfo:
    has_next = result.total_pages > 0 and result.page < result.total_pages
    has_previous = result.page > 1
    return ListPaginationInfo(
        page=result.page,
        page_size=result.page_size,
        total_items=result.total,
        total_pages=result.total_pages,
        has_next=has_next,
        has_previous=has_previous,
    )


def build_list_response(
    items: list[T],
    *,
    page: int,
    page_size: int,
    total: int,
    sort_field: str,
    sort_direction: SortDirection,
    filters: dict[str, Any] | None = None,
) -> StandardListResponse[T]:
    from app.core.pagination import build_paginated_meta

    meta = build_paginated_meta(page, page_size, total)
    return StandardListResponse(
        items=items,
        pagination=pagination_info_from_result(meta),
        sorting=ListSortingInfo(field=sort_field, direction=sort_direction),
        filters=filters or {},
    )
