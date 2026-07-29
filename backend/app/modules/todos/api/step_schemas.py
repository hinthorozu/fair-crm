from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    detail: str


class TodoStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    todo_id: UUID
    title: str
    sort_order: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime


class ReplaceTodoStepItemRequest(BaseModel):
    id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=500)


class ReplaceTodoStepsRequest(BaseModel):
    steps: list[ReplaceTodoStepItemRequest] = Field(default_factory=list)


class UpdateTodoStepRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    is_completed: Optional[bool] = None
