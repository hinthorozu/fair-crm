from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class QuoteSelectedItem(BaseModel):
    content_id: UUID
    value: str = Field(..., min_length=1, max_length=255)


class QuoteWriteRequest(BaseModel):
    template_id: UUID
    quote_date: date
    status: Literal["draft", "given"] = "draft"
    price: str = Field(default="", max_length=255)
    selected_items: list[QuoteSelectedItem] = Field(default_factory=list)


class QuoteResponse(BaseModel):
    id: UUID
    organization_id: UUID
    todo_id: UUID
    customer_id: UUID
    fair_id: UUID
    template_id: UUID
    quote_date: date
    status: str
    price: str
    selected_items: list[dict]
    created_at: datetime
    updated_at: datetime


class QuoteRenderResponse(BaseModel):
    html: str
