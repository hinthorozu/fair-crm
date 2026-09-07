from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrganizationClosureExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    status: str
    current_phase: str
    attempt_count: int
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime
    last_retry_at: datetime | None
