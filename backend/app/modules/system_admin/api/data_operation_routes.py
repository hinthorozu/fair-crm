from typing import Annotated
from uuid import UUID

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.api.dependencies.list_query import parse_list_query
from app.api.schemas.list_response import StandardListResponse, build_list_response
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.customers.api.routes import _to_response as customer_to_response
from app.modules.customers.api.schemas import CustomerResponse
from app.modules.customers.application.commands import CustomerResult
from app.modules.customers.application.duplicate_group_merge import DuplicateGroupMergePreviewResult
from app.modules.customers.application.duplicate_group_merge_execute import DuplicateGroupMergeExecuteResult
from app.modules.customers.application.duplicate_group_merge_idempotency import (
    try_get_idempotent_merge_execute_result,
)
from app.modules.customers.domain.communication_entities import (
    CustomerCommunications,
    CustomerEmail,
    CustomerPhone,
    CustomerWebsite,
)
from app.modules.customers.application.mappers import customer_results_with_communications, customer_to_result
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.system_admin.api.data_operation_schemas import (
    AssignCustomersToFairRequest,
    AssignCustomersToFairResponse,
    DeleteSelectedCustomersRequest,
    DeleteSelectedCustomersResponse,
    DataOperationDefinitionResponse,
    DataOperationRunResponse,
    DataOperationsListResponse,
    DuplicateDatasetCustomerResponse,
    DuplicateDatasetGroupDetailResponse,
    DuplicateDatasetGroupResponse,
    DuplicateGroupMergePreviewCommunicationResponse,
    DuplicateGroupMergePreviewIssueResponse,
    DuplicateGroupMergePreviewParticipationSummaryResponse,
    DuplicateGroupMergePreviewRequest,
    DuplicateGroupMergePreviewResponse,
    DuplicateGroupMergePreviewScalarFieldsResponse,
    DuplicateGroupMergePreviewStatisticsResponse,
    DuplicateGroupMergeExecuteRequest,
    DuplicateGroupMergeExecuteResponse,
    DuplicateGroupCustomerDetailResponse,
    DuplicateGroupParticipationResponse,
    RunDataOperationRequest,
    RunDataOperationResponse,
)
from app.modules.system_admin.api.dependencies import (
    access_token,
    get_data_operation_job_runner,
    get_assign_customers_to_fair_use_case,
    get_delete_selected_customers_use_case,
    get_download_data_operation_file_use_case,
    get_export_data_operation_dataset_customers_use_case,
    get_export_data_operation_duplicate_customers_use_case,
    get_get_data_operation_duplicate_group_detail_use_case,
    get_get_data_operation_run_use_case,
    get_list_data_operation_dataset_customers_use_case,
    get_list_data_operation_duplicate_customers_use_case,
    get_list_data_operation_duplicate_groups_use_case,
    get_list_data_operations_use_case,
    get_preview_duplicate_group_merge_use_case,
    get_execute_duplicate_group_merge_use_case,
    get_duplicate_group_merge_audit_recorder,
    get_run_data_operation_use_case,
    require_data_operations_read_permission,
    require_data_operations_run_permission,
)
from app.modules.system_admin.api.schemas import ErrorResponse
from app.modules.system_admin.application.data_operation_job_runner import DataOperationJobCommand
from app.shared.background_jobs import run_blocking_background_task
from app.modules.system_admin.application.data_operation_registry import get_operation_definition
from app.modules.system_admin.application.data_operation_service import (
    DATASET_CUSTOMER_ALLOWED_SORT_FIELDS,
    DATASET_DUPLICATE_CUSTOMER_ALLOWED_SORT_FIELDS,
    DATASET_DUPLICATE_GROUP_ALLOWED_SORT_FIELDS,
)
from app.modules.system_admin.application.duplicate_group_review import DUPLICATE_MERGE_POLICY
from app.modules.system_admin.infrastructure.repositories.data_operation_dataset_repository import (
    DatasetDuplicateCustomerItem,
    DatasetDuplicateGroupDetail,
    DatasetDuplicateGroupSummary,
    DuplicateGroupCustomerDetail,
)
from app.modules.system_admin.domain.data_operation_entities import DataOperationRun
from app.modules.customers.application.list_customers import DEFAULT_SORT_DIRECTION, DEFAULT_SORT_FIELD

router = APIRouter(prefix="/admin/data-operations", tags=["Admin — Data Operations"])
logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


def _customer_results_by_id(customers, db: Session) -> dict[UUID, CustomerResult]:
    if not customers:
        return {}
    comm_repo = SqlAlchemyCustomerCommunicationRepository(db)
    communications = comm_repo.load_for_customers([customer.id for customer in customers])
    results = customer_results_with_communications(customers, communications)
    return {result.id: result for result in results}


def _duplicate_item_to_response(
    item: DatasetDuplicateCustomerItem,
    customer_result: CustomerResult,
) -> DuplicateDatasetCustomerResponse:
    customer = customer_to_response(customer_result)
    return DuplicateDatasetCustomerResponse(
        id=customer.id,
        display_name=customer.display_name,
        legal_name=customer.legal_name,
        trade_name=customer.trade_name,
        customer_type=customer.customer_type,
        status=customer.status,
        phone=customer.phone,
        email=customer.email,
        website=customer.website,
        city=customer.city,
        country=customer.country,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        group_key=item.group_key,
        group_by=item.group_by,
        fair_count=item.fair_count,
        first_fair=item.first_fair_name,
        match_score=item.match_score,
        duplicate_reason=item.duplicate_reason,
        match_explanation=item.match_explanation,
        merge_classification=item.merge_classification,
    )


def _duplicate_group_to_response(summary: DatasetDuplicateGroupSummary) -> DuplicateDatasetGroupResponse:
    return DuplicateDatasetGroupResponse(
        group_key=summary.group_key,
        group_by=summary.group_by,
        customer_count=summary.customer_count,
        fair_count=summary.fair_count,
        fair_names=summary.fair_names,
        suggested_winner_customer_id=summary.suggested_winner_customer_id,
        suggested_winner_company_name=summary.suggested_winner_company_name,
        created_at_min=summary.created_at_min,
        created_at_max=summary.created_at_max,
        min_match_score=summary.min_match_score,
        max_match_score=summary.max_match_score,
        merge_classification=summary.merge_classification,
        review_tier=summary.review_tier,
        requires_manual_review=summary.requires_manual_review,
        match_explanation_summary=summary.match_explanation_summary,
    )


def _duplicate_group_customer_to_response(
    item: DuplicateGroupCustomerDetail,
    customer_result: CustomerResult,
) -> DuplicateGroupCustomerDetailResponse:
    customer = item.customer
    return DuplicateGroupCustomerDetailResponse(
        id=customer.id,
        company_name=customer.display_name,
        legal_name=customer.legal_name,
        trade_name=customer.trade_name,
        phone=customer_result.phone,
        email=customer_result.email,
        website=customer_result.website,
        phones=customer_result.phones or [],
        emails=customer_result.emails or [],
        websites=customer_result.websites or [],
        city=customer.city,
        country=customer.country,
        status=customer.status.value,
        created_at=customer.created_at,
        participations=[
            DuplicateGroupParticipationResponse(
                fair_name=participation.fair_name,
                fair_year=participation.fair_year,
                hall=participation.hall,
                stand=participation.stand,
            )
            for participation in item.participations
        ],
        match_score=item.match_score,
        duplicate_reason=item.duplicate_reason,
        match_explanation=item.match_explanation,
        merge_classification=item.merge_classification,
    )


def _duplicate_group_detail_to_response(
    detail: DatasetDuplicateGroupDetail,
    db: Session,
) -> DuplicateDatasetGroupDetailResponse:
    results_by_id = _customer_results_by_id(
        [item.customer for item in detail.customers],
        db,
    )
    return DuplicateDatasetGroupDetailResponse(
        group_key=detail.group_key,
        group_by=detail.group_by,
        customers=[
            _duplicate_group_customer_to_response(item, results_by_id[item.customer.id])
            for item in detail.customers
        ],
        merge_policy=DUPLICATE_MERGE_POLICY,
        min_match_score=detail.min_match_score,
        max_match_score=detail.max_match_score,
        merge_classification=detail.merge_classification,
        review_tier=detail.review_tier,
        requires_manual_review=detail.requires_manual_review,
        match_explanation_summary=detail.match_explanation_summary,
    )


def _preview_communications_from_merge(
    preview: DuplicateGroupMergePreviewResult,
) -> CustomerCommunications:
    customer_id = preview.surviving_customer_id
    timestamp = preview.merged_customer.updated_at
    return CustomerCommunications(
        emails=[
            CustomerEmail(
                id=item.source_row_id,
                customer_id=customer_id,
                email=item.value,
                is_primary=item.is_primary,
                created_at=timestamp,
            )
            for item in preview.emails
        ],
        phones=[
            CustomerPhone(
                id=item.source_row_id,
                customer_id=customer_id,
                phone=item.value,
                is_primary=item.is_primary,
                created_at=timestamp,
            )
            for item in preview.phones
        ],
        websites=[
            CustomerWebsite(
                id=item.source_row_id,
                customer_id=customer_id,
                website=item.value,
                is_primary=item.is_primary,
                created_at=timestamp,
            )
            for item in preview.websites
        ],
    )


def _merge_preview_to_response(preview: DuplicateGroupMergePreviewResult) -> DuplicateGroupMergePreviewResponse:
    merged_result = customer_to_result(
        preview.merged_customer,
        communications=_preview_communications_from_merge(preview),
    )
    return DuplicateGroupMergePreviewResponse(
        group_key=preview.group_key,
        group_by=preview.group_by,
        surviving_customer_id=preview.surviving_customer_id,
        merged_customer=customer_to_response(merged_result),
        scalar_fields=DuplicateGroupMergePreviewScalarFieldsResponse(
            company_name=preview.scalar_fields.company_name,
            legal_name=preview.scalar_fields.legal_name,
            trade_name=preview.scalar_fields.trade_name,
            city=preview.scalar_fields.city,
            country=preview.scalar_fields.country,
        ),
        emails=[
            DuplicateGroupMergePreviewCommunicationResponse(
                value=item.value,
                is_primary=item.is_primary,
                source_customer_id=item.source_customer_id,
                source_customer_name=item.source_customer_name,
                source_row_id=item.source_row_id,
            )
            for item in preview.emails
        ],
        phones=[
            DuplicateGroupMergePreviewCommunicationResponse(
                value=item.value,
                is_primary=item.is_primary,
                source_customer_id=item.source_customer_id,
                source_customer_name=item.source_customer_name,
                source_row_id=item.source_row_id,
            )
            for item in preview.phones
        ],
        websites=[
            DuplicateGroupMergePreviewCommunicationResponse(
                value=item.value,
                is_primary=item.is_primary,
                source_customer_id=item.source_customer_id,
                source_customer_name=item.source_customer_name,
                source_row_id=item.source_row_id,
            )
            for item in preview.websites
        ],
        participation_summary=DuplicateGroupMergePreviewParticipationSummaryResponse(
            total_participation_rows=preview.participation_summary.total_participation_rows,
            unique_fairs=preview.participation_summary.unique_fairs,
            fair_names=preview.participation_summary.fair_names,
        ),
        customers_to_archive=preview.customers_to_archive,
        validation_errors=[
            DuplicateGroupMergePreviewIssueResponse(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
            )
            for issue in preview.validation_errors
        ],
        warnings=[
            DuplicateGroupMergePreviewIssueResponse(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
            )
            for issue in preview.warnings
        ],
        statistics=DuplicateGroupMergePreviewStatisticsResponse(
            customers_before=preview.statistics.customers_before,
            customers_after=preview.statistics.customers_after,
            emails_before=preview.statistics.emails_before,
            emails_after=preview.statistics.emails_after,
            phones_before=preview.statistics.phones_before,
            phones_after=preview.statistics.phones_after,
            websites_before=preview.statistics.websites_before,
            websites_after=preview.statistics.websites_after,
        ),
        is_valid=preview.is_valid,
    )


def _merge_statistics_to_response(statistics) -> DuplicateGroupMergePreviewStatisticsResponse:
    return DuplicateGroupMergePreviewStatisticsResponse(
        customers_before=statistics.customers_before,
        customers_after=statistics.customers_after,
        emails_before=statistics.emails_before,
        emails_after=statistics.emails_after,
        phones_before=statistics.phones_before,
        phones_after=statistics.phones_after,
        websites_before=statistics.websites_before,
        websites_after=statistics.websites_after,
    )


def _merge_execute_to_response(
    result: DuplicateGroupMergeExecuteResult,
    db: Session,
    *,
    audit_log_id: UUID | None = None,
) -> DuplicateGroupMergeExecuteResponse:
    comm_repo = SqlAlchemyCustomerCommunicationRepository(db)
    communications = comm_repo.load_for_customer(result.surviving_customer.id)
    surviving_result = customer_to_result(result.surviving_customer, communications=communications)
    return DuplicateGroupMergeExecuteResponse(
        group_key=result.group_key,
        group_by=result.group_by,
        surviving_customer=customer_to_response(surviving_result),
        customers_deleted=result.customers_deleted,
        statistics=_merge_statistics_to_response(result.statistics),
        audit_log_id=audit_log_id,
    )


def _merge_execute_failure_detail(exc: Exception) -> str:
    if isinstance(exc, ProgrammingError):
        message = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        if "system_duplicate_group_merge_audit_logs" in message:
            return (
                "Merge audit log table is missing. "
                "Run database migrations (alembic upgrade head) and retry."
            )
        return f"Database schema error: {message}"
    return str(exc) or "Merge execute failed"


def _safe_idempotent_merge_execute_result(
    db: Session,
    *,
    organization_id: UUID,
    run_id: UUID,
    group_key: str,
    surviving_customer_id: UUID,
) -> DuplicateGroupMergeExecuteResult | None:
    try:
        return try_get_idempotent_merge_execute_result(
            db,
            organization_id=organization_id,
            run_id=run_id,
            group_key=group_key,
            surviving_customer_id=surviving_customer_id,
        )
    except Exception:
        logger.exception("Failed to load idempotent merge execute result")
        return None


def _run_to_response(run: DataOperationRun) -> DataOperationRunResponse:
    definition = get_operation_definition(run.operation_key)
    dataset_kind = (run.summary_json or {}).get("dataset_kind")
    return DataOperationRunResponse(
        id=run.id,
        operation_key=run.operation_key,
        status=run.status.value,
        started_by=run.started_by,
        started_by_email=run.started_by_email,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_seconds=run.duration_seconds,
        result=run.result.value if run.result else None,
        error_message=run.error_message,
        output_files=[
            {
                "id": file.id,
                "file_name": file.file_name,
                "relative_path": file.relative_path,
                "size_bytes": file.size_bytes,
            }
            for file in run.output_files
        ],
        summary_json=run.summary_json,
        result_mode=definition.result_mode if definition else None,
        dataset_kind=str(dataset_kind) if dataset_kind else None,
    )


def _definition_to_response(entry: dict) -> DataOperationDefinitionResponse:
    definition = entry["definition"]
    return DataOperationDefinitionResponse(
        key=definition.key,
        name=definition.name,
        description=definition.description,
        destructive=definition.destructive,
        output_mode=definition.output_mode,
        result_mode=definition.result_mode,
        dataset_kind=definition.dataset_kind,
        last_run=_run_to_response(entry["last_run"]) if entry["last_run"] else None,
        active_run=_run_to_response(entry["active_run"]) if entry["active_run"] else None,
    )


@router.get(
    "",
    response_model=DataOperationsListResponse,
    responses={403: {"model": ErrorResponse}},
    summary="List registered data operations with latest run metadata",
)
def list_data_operations(
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_list_data_operations_use_case),
) -> DataOperationsListResponse:
    try:
        items = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return DataOperationsListResponse(items=[_definition_to_response(entry) for entry in items])


@router.post(
    "/{operation_key}/run",
    response_model=RunDataOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Run a data operation (background job)",
)
def run_data_operation(
    operation_key: str,
    background_tasks: BackgroundTasks,
    body: RunDataOperationRequest | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_data_operations_run_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_run_data_operation_use_case),
    job_runner=Depends(get_data_operation_job_runner),
) -> RunDataOperationResponse:
    definition = get_operation_definition(operation_key)
    request_body = body or RunDataOperationRequest()
    try:
        run = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            user_email=auth.email,
            access_token=access_token(credentials),
            operation_key=operation_key,
            group_by=request_body.group_by,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    db.commit()
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_operation,
        DataOperationJobCommand(organization_id=auth.organization_id, run_id=run.id),
    )
    return RunDataOperationResponse(
        id=run.id,
        operation_key=run.operation_key,
        status=run.status.value,
        result_mode=definition.result_mode if definition else None,
        dataset_kind=definition.dataset_kind if definition else None,
    )


@router.get(
    "/runs/{run_id}",
    response_model=DataOperationRunResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get data operation run status",
)
def get_data_operation_run(
    run_id: UUID,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_get_data_operation_run_use_case),
) -> DataOperationRunResponse:
    try:
        run = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=run_id,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _run_to_response(run)


@router.post(
    "/runs/{run_id}/assign-fair",
    response_model=AssignCustomersToFairResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Assign selected customers from an analyze run to a fair (background job)",
)
def assign_customers_to_fair(
    run_id: UUID,
    body: AssignCustomersToFairRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_data_operations_run_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_assign_customers_to_fair_use_case),
    job_runner=Depends(get_data_operation_job_runner),
) -> AssignCustomersToFairResponse:
    try:
        run = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            user_email=auth.email,
            access_token=access_token(credentials),
            parent_run_id=run_id,
            fair_id=body.fair_id,
            customer_ids=body.customer_ids,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_assign_customers_to_fair,
        DataOperationJobCommand(organization_id=auth.organization_id, run_id=run.id),
    )
    payload = run.summary_json or {}
    return AssignCustomersToFairResponse(
        id=run.id,
        operation_key=run.operation_key,
        status=run.status.value,
        parent_run_id=run_id,
        fair_id=body.fair_id,
        selected_count=int(payload.get("selected_count", len(body.customer_ids))),
    )


@router.post(
    "/runs/{run_id}/delete-customers",
    response_model=DeleteSelectedCustomersResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Physically delete selected customers from an analyze run (background job)",
)
def delete_selected_customers(
    run_id: UUID,
    body: DeleteSelectedCustomersRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_data_operations_run_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_delete_selected_customers_use_case),
    job_runner=Depends(get_data_operation_job_runner),
) -> DeleteSelectedCustomersResponse:
    try:
        run = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            user_email=auth.email,
            access_token=access_token(credentials),
            parent_run_id=run_id,
            customer_ids=body.customer_ids,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    background_tasks.add_task(
        run_blocking_background_task,
        job_runner.run_delete_selected_customers,
        DataOperationJobCommand(organization_id=auth.organization_id, run_id=run.id),
    )
    payload = run.summary_json or {}
    return DeleteSelectedCustomersResponse(
        id=run.id,
        operation_key=run.operation_key,
        status=run.status.value,
        parent_run_id=run_id,
        selected_count=int(payload.get("selected_count", len(body.customer_ids))),
    )


@router.get(
    "/runs/{run_id}/dataset/customers",
    response_model=StandardListResponse[CustomerResponse],
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="List customers from a completed dataset operation run",
)
def list_data_operation_dataset_customers(
    run_id: UUID,
    request: Request,
    customer_status: CustomerStatus | None = Query(default=None, alias="status"),
    customer_type: CustomerType | None = Query(default=None),
    country: str | None = Query(default=None, max_length=100),
    search: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 25,
    sort: Annotated[str | None, Query(validation_alias=AliasChoices("sort_by", "sort"))] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    sort_order: Annotated[str | None, Query(pattern="^(?i)(asc|desc)$")] = None,
    direction: Annotated[
        str | None,
        Query(pattern="^(?i)(asc|desc)$", validation_alias=AliasChoices("sort_dir", "direction")),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_list_data_operation_dataset_customers_use_case),
    db: Session = Depends(get_db),
) -> StandardListResponse[CustomerResponse]:
    list_query = parse_list_query(
        page=page,
        page_size=page_size,
        search=search,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order or request.query_params.get("sort_order"),
        default_sort=DEFAULT_SORT_FIELD,
        allowed_sort_fields=DATASET_CUSTOMER_ALLOWED_SORT_FIELDS,
        default_direction=DEFAULT_SORT_DIRECTION,
    )
    try:
        result, resolved_sort, resolved_dir = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=run_id,
            status=customer_status,
            customer_type=customer_type,
            country=country.strip() if country and country.strip() else None,
            search=list_query.search,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    filters: dict[str, str] = {}
    if list_query.search:
        filters["search"] = list_query.search
    if customer_status is not None:
        filters["status"] = customer_status.value
    if customer_type is not None:
        filters["customerType"] = customer_type.value
    if country and country.strip():
        filters["country"] = country.strip()

    results_by_id = _customer_results_by_id(result.items, db)
    return build_list_response(
        [customer_to_response(results_by_id[item.id]) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        sort_field=resolved_sort,
        sort_direction=resolved_dir,
        filters=filters,
    )


@router.get(
    "/runs/{run_id}/dataset/customers/export",
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Export dataset operation customers to Excel",
)
def export_data_operation_dataset_customers(
    run_id: UUID,
    request: Request,
    customer_status: CustomerStatus | None = Query(default=None, alias="status"),
    customer_type: CustomerType | None = Query(default=None),
    country: str | None = Query(default=None, max_length=100),
    search: str | None = Query(default=None),
    sort: Annotated[str | None, Query(validation_alias=AliasChoices("sort_by", "sort"))] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    sort_order: Annotated[str | None, Query(pattern="^(?i)(asc|desc)$")] = None,
    direction: Annotated[
        str | None,
        Query(pattern="^(?i)(asc|desc)$", validation_alias=AliasChoices("sort_dir", "direction")),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_export_data_operation_dataset_customers_use_case),
):
    list_query = parse_list_query(
        page=1,
        page_size=25,
        search=search,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order or request.query_params.get("sort_order"),
        default_sort=DEFAULT_SORT_FIELD,
        allowed_sort_fields=DATASET_CUSTOMER_ALLOWED_SORT_FIELDS,
        default_direction=DEFAULT_SORT_DIRECTION,
    )
    try:
        file_name, buffer = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=run_id,
            status=customer_status,
            customer_type=customer_type,
            country=country.strip() if country and country.strip() else None,
            search=list_query.search,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get(
    "/runs/{run_id}/dataset/duplicate-groups",
    response_model=StandardListResponse[DuplicateDatasetGroupResponse],
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="List duplicate groups from a completed duplicate analysis run",
)
def list_data_operation_duplicate_groups(
    run_id: UUID,
    request: Request,
    search: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 25,
    sort: Annotated[str | None, Query(validation_alias=AliasChoices("sort_by", "sort"))] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    sort_order: Annotated[str | None, Query(pattern="^(?i)(asc|desc)$")] = None,
    direction: Annotated[
        str | None,
        Query(pattern="^(?i)(asc|desc)$", validation_alias=AliasChoices("sort_dir", "direction")),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_list_data_operation_duplicate_groups_use_case),
) -> StandardListResponse[DuplicateDatasetGroupResponse]:
    list_query = parse_list_query(
        page=page,
        page_size=page_size,
        search=search,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order or request.query_params.get("sort_order"),
        default_sort="group_key",
        allowed_sort_fields=DATASET_DUPLICATE_GROUP_ALLOWED_SORT_FIELDS,
        default_direction=DEFAULT_SORT_DIRECTION,
    )
    try:
        result, resolved_sort, resolved_dir = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=run_id,
            search=list_query.search,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    filters: dict[str, str | int] = {
        "liveDuplicateGroups": result.live_duplicate_groups,
        "liveCustomersInDuplicateGroups": result.live_customers_in_duplicate_groups,
    }
    if list_query.search:
        filters["search"] = list_query.search

    return build_list_response(
        [_duplicate_group_to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        sort_field=resolved_sort,
        sort_direction=resolved_dir,
        filters=filters,
    )


@router.get(
    "/runs/{run_id}/dataset/duplicate-groups/{group_key}",
    response_model=DuplicateDatasetGroupDetailResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get duplicate group review detail",
)
def get_data_operation_duplicate_group_detail(
    run_id: UUID,
    group_key: str,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_get_data_operation_duplicate_group_detail_use_case),
    db: Session = Depends(get_db),
) -> DuplicateDatasetGroupDetailResponse:
    try:
        detail = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=run_id,
            group_key=group_key,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _duplicate_group_detail_to_response(detail, db)


@router.post(
    "/duplicate-groups/{group_key}/merge-preview",
    response_model=DuplicateGroupMergePreviewResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Preview duplicate group merge without modifying data",
)
def preview_duplicate_group_merge(
    group_key: str,
    body: DuplicateGroupMergePreviewRequest,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_preview_duplicate_group_merge_use_case),
) -> DuplicateGroupMergePreviewResponse:
    try:
        preview = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=body.run_id,
            group_key=group_key,
            surviving_customer_id=body.surviving_customer_id,
            scalar_selections=body.scalar_selections.model_dump(),
            selected_email_ids=body.selected_email_ids,
            selected_phone_ids=body.selected_phone_ids,
            selected_website_ids=body.selected_website_ids,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _merge_preview_to_response(preview)


@router.post(
    "/duplicate-groups/{group_key}/merge-execute",
    response_model=DuplicateGroupMergeExecuteResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
    summary="Execute duplicate group merge",
)
def execute_duplicate_group_merge(
    group_key: str,
    body: DuplicateGroupMergeExecuteRequest,
    auth: AuthContext = Depends(require_data_operations_run_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_execute_duplicate_group_merge_use_case),
    audit_recorder=Depends(get_duplicate_group_merge_audit_recorder),
    db: Session = Depends(get_db),
) -> DuplicateGroupMergeExecuteResponse:
    savepoint = db.begin_nested()
    result: DuplicateGroupMergeExecuteResult | None = None
    audit_log_id: UUID | None = None
    try:
        result = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=body.run_id,
            group_key=group_key,
            surviving_customer_id=body.surviving_customer_id,
            scalar_selections=body.scalar_selections.model_dump(),
            selected_email_ids=body.selected_email_ids,
            selected_phone_ids=body.selected_phone_ids,
            selected_website_ids=body.selected_website_ids,
        )
        audit_record = audit_recorder.record(
            organization_id=auth.organization_id,
            executed_by_user_id=auth.user_id,
            executed_by_user_email=auth.email,
            run_id=body.run_id,
            merge_result=result,
            scalar_selections=body.scalar_selections.model_dump(),
            selected_email_ids=body.selected_email_ids,
            selected_phone_ids=body.selected_phone_ids,
            selected_website_ids=body.selected_website_ids,
        )
        audit_log_id = audit_record.id
        savepoint.commit()
    except ForbiddenError as exc:
        savepoint.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        savepoint.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        savepoint.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        savepoint.rollback()
        raise
    except ProgrammingError as exc:
        savepoint.rollback()
        logger.exception("Duplicate group merge execute schema error for group_key=%s", group_key)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_merge_execute_failure_detail(exc),
        ) from exc
    except Exception as exc:
        savepoint.rollback()
        existing = _safe_idempotent_merge_execute_result(
            db,
            organization_id=auth.organization_id,
            run_id=body.run_id,
            group_key=group_key,
            surviving_customer_id=body.surviving_customer_id,
        )
        if existing is not None:
            return _merge_execute_to_response(existing, db)
        logger.exception("Duplicate group merge execute failed for group_key=%s", group_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_merge_execute_failure_detail(exc),
        ) from exc

    assert result is not None
    try:
        return _merge_execute_to_response(result, db, audit_log_id=audit_log_id)
    except Exception as exc:
        existing = _safe_idempotent_merge_execute_result(
            db,
            organization_id=auth.organization_id,
            run_id=body.run_id,
            group_key=group_key,
            surviving_customer_id=body.surviving_customer_id,
        )
        if existing is not None:
            return _merge_execute_to_response(existing, db)
        logger.exception("Failed to build merge execute response for group_key=%s", group_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc) or "Failed to build merge execute response",
        ) from exc


@router.get(
    "/runs/{run_id}/dataset/duplicate-customers",
    response_model=StandardListResponse[DuplicateDatasetCustomerResponse],
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="List duplicate customers from a completed dataset operation run",
)
def list_data_operation_duplicate_customers(
    run_id: UUID,
    request: Request,
    customer_status: CustomerStatus | None = Query(default=None, alias="status"),
    customer_type: CustomerType | None = Query(default=None),
    country: str | None = Query(default=None, max_length=100),
    search: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 25,
    sort: Annotated[str | None, Query(validation_alias=AliasChoices("sort_by", "sort"))] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    sort_order: Annotated[str | None, Query(pattern="^(?i)(asc|desc)$")] = None,
    direction: Annotated[
        str | None,
        Query(pattern="^(?i)(asc|desc)$", validation_alias=AliasChoices("sort_dir", "direction")),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_list_data_operation_duplicate_customers_use_case),
    db: Session = Depends(get_db),
) -> StandardListResponse[DuplicateDatasetCustomerResponse]:
    list_query = parse_list_query(
        page=page,
        page_size=page_size,
        search=search,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order or request.query_params.get("sort_order"),
        default_sort="group_key",
        allowed_sort_fields=DATASET_DUPLICATE_CUSTOMER_ALLOWED_SORT_FIELDS,
        default_direction=DEFAULT_SORT_DIRECTION,
    )
    try:
        result, resolved_sort, resolved_dir = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=run_id,
            status=customer_status,
            customer_type=customer_type,
            country=country.strip() if country and country.strip() else None,
            search=list_query.search,
            page=list_query.page,
            page_size=list_query.page_size,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    filters: dict[str, str] = {}
    if list_query.search:
        filters["search"] = list_query.search
    if customer_status is not None:
        filters["status"] = customer_status.value
    if customer_type is not None:
        filters["customerType"] = customer_type.value
    if country and country.strip():
        filters["country"] = country.strip()

    results_by_id = _customer_results_by_id([item.customer for item in result.items], db)
    return build_list_response(
        [_duplicate_item_to_response(item, results_by_id[item.customer.id]) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        sort_field=resolved_sort,
        sort_direction=resolved_dir,
        filters=filters,
    )


@router.get(
    "/runs/{run_id}/dataset/duplicate-customers/export",
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Export duplicate dataset operation customers to Excel",
)
def export_data_operation_duplicate_customers(
    run_id: UUID,
    request: Request,
    customer_status: CustomerStatus | None = Query(default=None, alias="status"),
    customer_type: CustomerType | None = Query(default=None),
    country: str | None = Query(default=None, max_length=100),
    search: str | None = Query(default=None),
    sort: Annotated[str | None, Query(validation_alias=AliasChoices("sort_by", "sort"))] = None,
    sort_by: Annotated[str | None, Query(include_in_schema=False)] = None,
    sort_order: Annotated[str | None, Query(pattern="^(?i)(asc|desc)$")] = None,
    direction: Annotated[
        str | None,
        Query(pattern="^(?i)(asc|desc)$", validation_alias=AliasChoices("sort_dir", "direction")),
    ] = None,
    sort_dir: Annotated[str | None, Query(include_in_schema=False)] = None,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_export_data_operation_duplicate_customers_use_case),
):
    list_query = parse_list_query(
        page=1,
        page_size=25,
        search=search,
        sort=sort,
        sort_by=sort_by,
        direction=direction,
        sort_dir=sort_dir,
        sort_order=sort_order or request.query_params.get("sort_order"),
        default_sort="group_key",
        allowed_sort_fields=DATASET_DUPLICATE_CUSTOMER_ALLOWED_SORT_FIELDS,
        default_direction=DEFAULT_SORT_DIRECTION,
    )
    try:
        file_name, buffer = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=run_id,
            status=customer_status,
            customer_type=customer_type,
            country=country.strip() if country and country.strip() else None,
            search=list_query.search,
            sort_by=list_query.sort_by,
            sort_dir=list_query.sort_dir,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get(
    "/runs/{run_id}/files/{file_id}/download",
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Download generated data operation output file",
)
def download_data_operation_file(
    run_id: UUID,
    file_id: UUID,
    auth: AuthContext = Depends(require_data_operations_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_download_data_operation_file_use_case),
):
    try:
        _run, file_name, path = use_case.execute(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=access_token(credentials),
            run_id=run_id,
            file_id=file_id,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=file_name,
    )
