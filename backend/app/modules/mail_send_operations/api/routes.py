from datetime import datetime, time, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.list_helpers import standard_list_from_result
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.mail_send_operations.api.dependencies import (
    get_list_mail_send_operations_use_case,
    get_retry_mail_send_operation_use_case,
    require_read_permission,
    require_update_permission,
)
from app.modules.mail_send_operations.api.schemas import (
    ErrorResponse,
    MailOperationLogEntryResponse,
    MailSendOperationListItemResponse,
    MailSendOperationListResponse,
    RetryMailSendOperationResponse,
)
from app.modules.mail_send_operations.application.commands import (
    ListMailSendOperationsQuery,
    RetryMailSendOperationCommand,
)
from app.modules.mail_send_operations.application.list_mail_send_operations import (
    ListMailSendOperationsUseCase,
    MailSendOperationListItem,
)
from app.modules.mail_send_operations.application.retry_mail_send_operation import (
    RetryMailSendOperationUseCase,
)
from app.modules.mail_send_operations.domain.exceptions import (
    InvalidMailSendOperationTransitionError,
    MailSendOperationNotFoundError,
    MailSendOperationRetryNotSupportedError,
)

router = APIRouter(prefix="/mail-send-operations", tags=["mail-send-operations"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _parse_date_start(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_from") from exc
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


def _parse_date_end(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_to") from exc
    return datetime.combine(parsed, time.max, tzinfo=timezone.utc)


def _to_response(item: MailSendOperationListItem) -> MailSendOperationListItemResponse:
    logs = [
        MailOperationLogEntryResponse(
            time=str(entry.get("time", "")),
            event=str(entry.get("event", "")),
            message=str(entry.get("message", "")),
        )
        for entry in (item.operation_logs or [])
        if isinstance(entry, dict)
    ]
    return MailSendOperationListItemResponse(
        id=item.id,
        created_at=item.created_at,
        source_type=item.source_type,
        source_type_label=item.source_type_label,
        fair_id=item.fair_id,
        fair_name=item.fair_name,
        customer_id=item.customer_id,
        customer_name=item.customer_name,
        recipient_email=item.recipient_email,
        recipient_name=item.recipient_name,
        smtp_account_id=item.smtp_account_id,
        smtp_account_name=item.smtp_account_name,
        template_id=item.template_id,
        template_name=item.template_name,
        subject=item.subject,
        status=item.status,
        status_label=item.status_label,
        error_code=item.error_code,
        error_message=item.error_message,
        operation_logs=logs,
        retry_count=item.retry_count,
        priority=item.priority,
        sent_at=item.sent_at,
        failed_at=item.failed_at,
        cancelled_at=item.cancelled_at,
    )


@router.get(
    "",
    response_model=MailSendOperationListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_mail_send_operations(
    auth: AuthContext = Depends(require_read_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: ListMailSendOperationsUseCase = Depends(get_list_mail_send_operations_use_case),
    search: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    source_type: Annotated[str | None, Query()] = None,
    smtp_account_id: Annotated[UUID | None, Query()] = None,
    fair_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> MailSendOperationListResponse:
    result = use_case.execute(
        ListMailSendOperationsQuery(
            organization_id=auth.organization_id,
            user_id=auth.user_id,
            access_token=_access_token(credentials),
            search=search,
            status=status,
            source_type=source_type,
            smtp_account_id=smtp_account_id,
            fair_id=fair_id,
            date_from=_parse_date_start(date_from),
            date_to=_parse_date_end(date_to),
            page=page,
            page_size=page_size,
        )
    )
    filters = {
        key: value
        for key, value in {
            "search": search,
            "status": status,
            "source_type": source_type,
            "smtp_account_id": str(smtp_account_id) if smtp_account_id else None,
            "fair_id": str(fair_id) if fair_id else None,
            "date_from": date_from,
            "date_to": date_to,
        }.items()
        if value
    }
    response = standard_list_from_result(
        result,
        sort_field="created_at",
        sort_direction="desc",
        filters=filters,
    )
    return MailSendOperationListResponse(
        items=[_to_response(item) for item in result.items],
        pagination=response.pagination.model_dump(by_alias=True),
        sorting=response.sorting.model_dump(),
        filters=response.filters,
    )


@router.post(
    "/{operation_id}/retry",
    response_model=RetryMailSendOperationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def retry_mail_send_operation(
    operation_id: UUID,
    auth: AuthContext = Depends(require_update_permission),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case: RetryMailSendOperationUseCase = Depends(get_retry_mail_send_operation_use_case),
) -> RetryMailSendOperationResponse:
    try:
        result = use_case.execute(
            RetryMailSendOperationCommand(
                organization_id=auth.organization_id,
                user_id=auth.user_id,
                access_token=_access_token(credentials),
                operation_id=operation_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MailSendOperationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (
        InvalidMailSendOperationTransitionError,
        MailSendOperationRetryNotSupportedError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RetryMailSendOperationResponse(
        success=result.success,
        operation=_to_response(result.operation),
    )
