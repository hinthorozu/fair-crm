from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class OrganizationClosureCredentialDispositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    closure_execution_id: UUID
    email_account_id: UUID
    account_type: str
    provider_key: str | None
    capability_class: str
    external_invalidation_state: str
    target_verification_state: str
    external_credential_id: str | None
    status: str
    signing_secret_retained: bool
    attempt_count: int
    failure_code: str | None
    failure_message: str | None
    outbound_disabled_at: datetime
    external_invalidated_at: datetime | None
    send_secret_purged_at: datetime | None
    created_at: datetime
    updated_at: datetime
    last_retry_at: datetime | None


class OrganizationClosureCredentialDispositionListResponse(BaseModel):
    items: list[OrganizationClosureCredentialDispositionResponse]


class OrganizationClosureCredentialReconcileRequest(BaseModel):
    action: Literal["record_target", "confirm_external_invalidation"]
    external_credential_id: str | None = Field(default=None, max_length=200)
    evidence_code: str | None = Field(default=None, max_length=128)
    evidence_reference: str | None = Field(default=None, max_length=255)
