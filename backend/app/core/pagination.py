"""Shared offset pagination helpers for Fair CRM list endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Literal

SortDirection = Literal["asc", "desc"]

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class PaginatedResult:
    page: int
    page_size: int
    total: int
    total_pages: int


def normalize_page_params(page: int, page_size: int) -> PageParams:
    safe_page = max(1, page)
    safe_size = min(max(1, page_size), MAX_PAGE_SIZE)
    return PageParams(page=safe_page, page_size=safe_size)


def compute_total_pages(total: int, page_size: int) -> int:
    if total <= 0:
        return 0
    return ceil(total / page_size)


def build_paginated_meta(page: int, page_size: int, total: int) -> PaginatedResult:
    return PaginatedResult(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=compute_total_pages(total, page_size),
    )


def normalize_sort_direction(sort_dir: str | None) -> SortDirection:
    if sort_dir and sort_dir.strip().lower() == "asc":
        return "asc"
    return "desc"
