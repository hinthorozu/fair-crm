from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CostUnit = Literal["Adet", "Kg", "m²", "Metre", "Gün", "Saat"]
CostCurrency = Literal["TL", "USD"]


class CostCategoryWriteRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class CostCategoryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class CostCategoryListResponse(BaseModel):
    items: list[CostCategoryResponse]


class CostCategoryOptionResponse(BaseModel):
    id: UUID
    name: str


class CostCategoryOptionsResponse(BaseModel):
    items: list[CostCategoryOptionResponse]


class CostProductWriteRequest(BaseModel):
    category_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    unit: CostUnit
    unit_price: Decimal = Field(..., ge=0, decimal_places=4)
    currency: CostCurrency


class CostProductResponse(BaseModel):
    id: UUID
    organization_id: UUID
    category_id: UUID
    category_name: str
    name: str
    slug: str
    unit: CostUnit
    unit_price: Decimal
    currency: CostCurrency
    created_at: datetime
    updated_at: datetime


class CostProductListResponse(BaseModel):
    items: list[CostProductResponse]
