from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.customers.api.schemas import (
    CustomerEmailResponse,
    CustomerPhoneResponse,
    CustomerResponse,
    CustomerWebsiteResponse,
)


class DataOperationOutputFileResponse(BaseModel):
    id: UUID
    file_name: str
    relative_path: str
    size_bytes: int | None = None


class DataOperationRunResponse(BaseModel):
    id: UUID
    operation_key: str
    status: str
    started_by: UUID
    started_by_email: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    result: str | None
    error_message: str | None
    output_files: list[DataOperationOutputFileResponse] = Field(default_factory=list)
    summary_json: dict[str, Any] | None = None
    result_mode: str | None = None
    dataset_kind: str | None = None


class DataOperationDefinitionResponse(BaseModel):
    key: str
    name: str
    description: str
    destructive: bool
    output_mode: str
    result_mode: str
    dataset_kind: str | None = None
    last_run: DataOperationRunResponse | None = None
    active_run: DataOperationRunResponse | None = None


class DataOperationsListResponse(BaseModel):
    items: list[DataOperationDefinitionResponse]


class RunDataOperationRequest(BaseModel):
    group_by: str | None = Field(
        default=None,
        description="Grouping field for duplicate customer analysis: company_name, email, website, or phone",
    )


class RunDataOperationResponse(BaseModel):
    id: UUID
    operation_key: str
    status: str
    result_mode: str | None = None
    dataset_kind: str | None = None


class AssignCustomersToFairRequest(BaseModel):
    fair_id: UUID
    customer_ids: list[UUID] = Field(min_length=1)


class AssignCustomersToFairResponse(BaseModel):
    id: UUID
    operation_key: str
    status: str
    parent_run_id: UUID
    fair_id: UUID
    selected_count: int


class DeleteSelectedCustomersRequest(BaseModel):
    customer_ids: list[UUID] = Field(min_length=1)


class DeleteSelectedCustomersResponse(BaseModel):
    id: UUID
    operation_key: str
    status: str
    parent_run_id: UUID
    selected_count: int


class DuplicateDatasetCustomerResponse(BaseModel):
    id: UUID
    display_name: str
    legal_name: str | None = None
    trade_name: str | None = None
    customer_type: str
    status: str
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    city: str | None = None
    country: str | None = None
    created_at: datetime
    updated_at: datetime
    group_key: str
    group_by: str | None = None
    fair_count: int
    first_fair: str | None = None
    match_score: int | None = None
    duplicate_reason: str | None = None
    match_explanation: str | None = None
    merge_classification: str | None = None


class DuplicateDatasetGroupResponse(BaseModel):
    group_key: str
    group_by: str
    customer_count: int
    fair_count: int
    fair_names: list[str]
    suggested_winner_customer_id: UUID
    suggested_winner_company_name: str
    created_at_min: datetime
    created_at_max: datetime
    min_match_score: int | None = None
    max_match_score: int | None = None
    merge_classification: str | None = None
    review_tier: str | None = None
    requires_manual_review: bool = False
    match_explanation_summary: str | None = None


class DuplicateGroupParticipationResponse(BaseModel):
    fair_name: str
    fair_year: int | None = None
    hall: str | None = None
    stand: str | None = None


class DuplicateGroupCustomerDetailResponse(BaseModel):
    id: UUID
    company_name: str
    legal_name: str | None = None
    trade_name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    phones: list[CustomerPhoneResponse] = Field(default_factory=list)
    emails: list[CustomerEmailResponse] = Field(default_factory=list)
    websites: list[CustomerWebsiteResponse] = Field(default_factory=list)
    city: str | None = None
    country: str | None = None
    status: str
    created_at: datetime
    participations: list[DuplicateGroupParticipationResponse]
    match_score: int | None = None
    duplicate_reason: str | None = None
    match_explanation: str | None = None
    merge_classification: str | None = None


class DuplicateDatasetGroupDetailResponse(BaseModel):
    group_key: str
    group_by: str
    customers: list[DuplicateGroupCustomerDetailResponse]
    merge_policy: str
    min_match_score: int | None = None
    max_match_score: int | None = None
    merge_classification: str | None = None
    review_tier: str | None = None
    requires_manual_review: bool = False
    match_explanation_summary: str | None = None


class DuplicateGroupScalarSelectionsRequest(BaseModel):
    company_name: UUID
    legal_name: UUID
    trade_name: UUID
    city: UUID
    country: UUID


class DuplicateGroupMergePreviewRequest(BaseModel):
    run_id: UUID
    surviving_customer_id: UUID
    scalar_selections: DuplicateGroupScalarSelectionsRequest
    selected_email_ids: list[UUID] = Field(default_factory=list)
    selected_phone_ids: list[UUID] = Field(default_factory=list)
    selected_website_ids: list[UUID] = Field(default_factory=list)


class DuplicateGroupMergePreviewCommunicationResponse(BaseModel):
    value: str
    is_primary: bool
    source_customer_id: UUID
    source_customer_name: str
    source_row_id: UUID


class DuplicateGroupMergePreviewScalarFieldsResponse(BaseModel):
    company_name: str
    legal_name: str | None = None
    trade_name: str | None = None
    city: str | None = None
    country: str | None = None


class DuplicateGroupMergePreviewParticipationSummaryResponse(BaseModel):
    total_participation_rows: int
    unique_fairs: int
    fair_names: list[str]


class DuplicateGroupMergePreviewStatisticsResponse(BaseModel):
    customers_before: int
    customers_after: int
    emails_before: int
    emails_after: int
    phones_before: int
    phones_after: int
    websites_before: int
    websites_after: int


class DuplicateGroupMergePreviewIssueResponse(BaseModel):
    code: str
    message: str
    severity: str


class DuplicateGroupMergePreviewResponse(BaseModel):
    group_key: str
    group_by: str
    surviving_customer_id: UUID
    merged_customer: CustomerResponse
    scalar_fields: DuplicateGroupMergePreviewScalarFieldsResponse
    emails: list[DuplicateGroupMergePreviewCommunicationResponse]
    phones: list[DuplicateGroupMergePreviewCommunicationResponse]
    websites: list[DuplicateGroupMergePreviewCommunicationResponse]
    participation_summary: DuplicateGroupMergePreviewParticipationSummaryResponse
    customers_to_archive: list[UUID]
    validation_errors: list[DuplicateGroupMergePreviewIssueResponse]
    warnings: list[DuplicateGroupMergePreviewIssueResponse]
    statistics: DuplicateGroupMergePreviewStatisticsResponse
    is_valid: bool


class DuplicateGroupMergeExecuteRequest(BaseModel):
    run_id: UUID
    surviving_customer_id: UUID
    scalar_selections: DuplicateGroupScalarSelectionsRequest
    selected_email_ids: list[UUID] = Field(default_factory=list)
    selected_phone_ids: list[UUID] = Field(default_factory=list)
    selected_website_ids: list[UUID] = Field(default_factory=list)


class DuplicateGroupMergeExecuteResponse(BaseModel):
    group_key: str
    group_by: str
    surviving_customer: CustomerResponse
    customers_deleted: list[UUID]
    statistics: DuplicateGroupMergePreviewStatisticsResponse
    audit_log_id: UUID | None = None
