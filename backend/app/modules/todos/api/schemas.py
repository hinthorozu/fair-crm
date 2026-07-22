from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.list_response import StandardListResponse
from app.modules.todos.domain.value_objects import TodoCategory, TodoPriority, TodoStatus

TodoStatusField = Literal[
    "todo",
    "in_progress",
    "done",
    "cancelled",
    "archived",
]

TodoPatchStatusField = Literal["todo", "in_progress", "cancelled"]

TodoPriorityField = Literal["low", "normal", "high", "urgent"]

TodoCategoryField = Literal[
    "arama",
    "toplu_mail",
    "sms",
    "whatsapp",
    "ziyaret",
    "teklif",
    "veri_temizleme",
    "import_kontrol",
    "musteri_guncelleme",
    "genel_gorev",
    "stand_tasarim",
    "diger",
]

CreatableTodoCategoryField = Literal[
    "arama",
    "ziyaret",
    "teklif",
    "import_kontrol",
    "musteri_guncelleme",
    "genel_gorev",
    "stand_tasarim",
    "diger",
]


class CreateTodoRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=10000)
    status: TodoStatusField = TodoStatus.TODO
    priority: TodoPriorityField = TodoPriority.NORMAL
    category: CreatableTodoCategoryField = TodoCategory.GENEL_GOREV
    deadline: Optional[datetime] = None
    assignee_user_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    source_fair_id: Optional[UUID] = None


class UpdateTodoRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=10000)
    status: Optional[TodoPatchStatusField] = None
    priority: Optional[TodoPriorityField] = None
    category: Optional[CreatableTodoCategoryField] = None
    deadline: Optional[datetime] = None
    assignee_user_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    source_fair_id: Optional[UUID] = None


class CompleteTodoRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=10000)


class TodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    category: str
    deadline: Optional[datetime]
    assignee_user_id: Optional[UUID]
    customer_id: Optional[UUID]
    source_fair_id: Optional[UUID]
    created_by: UUID
    updated_by: Optional[UUID]
    archived_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_overdue: bool


class TodoListResponse(StandardListResponse[TodoResponse]):
    pass


class ErrorResponse(BaseModel):
    detail: str
