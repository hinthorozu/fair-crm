from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse

OutcomePrimaryWorklistStatusField = Literal["in_follow_up", "closed"]

OutcomeActiveFilterField = Literal["true", "false", "all"]


class CreateTodoOutcomeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=64)
    primary_worklist_status: OutcomePrimaryWorklistStatusField
    description: Optional[str] = Field(default=None, max_length=10000)
    sort_order: int = 0
    requires_action: bool = False
    marks_data_problem: bool = False
    is_active: bool = True


class UpdateTodoOutcomeRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10000)
    primary_worklist_status: Optional[OutcomePrimaryWorklistStatusField] = None
    requires_action: Optional[bool] = None
    marks_data_problem: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class TodoOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    sort_order: int
    primary_worklist_status: str
    requires_action: bool
    marks_data_problem: bool
    created_at: datetime
    updated_at: datetime


class TodoOutcomeListResponse(StandardListResponse[TodoOutcomeResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str
