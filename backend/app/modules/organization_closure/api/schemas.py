from datetime import datetime
from typing import Any
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


class OrganizationClosureExportPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    closure_execution_id: UUID
    schema_version: str
    disposition: str
    status: str
    manifest_json: dict[str, Any]
    manifest_digest: str
    created_at: datetime
    updated_at: datetime
