"""Reusable OpenAPI pagination response fields."""

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    page: int = Field(..., ge=1, description="Current page (1-based)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total matching records")
    total_pages: int = Field(..., ge=0, description="Total pages for current page_size")
