"""Shared list query parameter parsing (ADR-015)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.core.pagination import (
    ALLOWED_PAGE_SIZES,
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    normalize_page_params,
    normalize_page_size,
    normalize_sort_direction,
    resolve_sort_field,
)


@dataclass(frozen=True)
class NormalizedListQuery:
    page: int
    page_size: int
    search: str | None
    sort_by: str
    sort_dir: str


def resolve_page_size_from_request(request: Request | None, fallback: int) -> int:
    if request is None:
        return fallback
    raw = request.query_params.get("pageSize") or request.query_params.get("page_size")
    if raw is None:
        return fallback
    try:
        return int(raw)
    except ValueError:
        return fallback


def parse_list_query(
    *,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    sort: str | None = None,
    sort_by: str | None = None,
    direction: str | None = None,
    sort_dir: str | None = None,
    sort_order: str | None = None,
    default_sort: str,
    allowed_sort_fields: frozenset[str],
    default_direction: str = "asc",
) -> NormalizedListQuery:
    page_params = normalize_page_params(page, normalize_page_size(page_size))
    requested_sort = sort_by or sort or default_sort
    sort_field = resolve_sort_field(requested_sort, allowed_sort_fields, default_sort)
    raw_direction = sort_order or sort_dir or direction or default_direction
    normalized_direction = normalize_sort_direction(raw_direction)
    normalized_search = search.strip() if search and search.strip() else None
    return NormalizedListQuery(
        page=page_params.page,
        page_size=page_params.page_size,
        search=normalized_search,
        sort_by=sort_field,
        sort_dir=normalized_direction,
    )


__all__ = [
    "ALLOWED_PAGE_SIZES",
    "NormalizedListQuery",
    "parse_list_query",
    "resolve_page_size_from_request",
]
