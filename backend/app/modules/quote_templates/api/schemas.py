from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuoteTemplateWriteRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    logo_url: str | None = Field(default=None, max_length=1024)
    source_code: str = Field(..., min_length=1)


class QuoteTemplateResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    current_version_id: UUID
    version_number: int
    logo_url: str | None
    source_code: str
    created_at: datetime
    updated_at: datetime


class QuoteTemplateListResponse(BaseModel):
    items: list[QuoteTemplateResponse]


class LogoUploadResponse(BaseModel):
    url: str
