from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TagResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class TagListResponse(BaseModel):
    items: list[TagResponse]


class ContentCreateRequest(BaseModel):
    tag_id: UUID
    title: str = Field(min_length=1, max_length=255)


class ContentResponse(BaseModel):
    id: UUID
    tag_id: UUID
    tag_name: str
    title: str
    created_at: datetime


class ContentListResponse(BaseModel):
    items: list[ContentResponse]
