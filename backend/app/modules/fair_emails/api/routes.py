from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fair_emails.api.dependencies import (
    get_auth_context,
    get_email_batch_detail_use_case,
    get_list_email_batches_use_case,
    get_preview_bulk_email_use_case,
    get_preview_recipients_use_case,
    get_send_bulk_email_use_case,
)
from app.modules.fair_emails.api.schemas import (
    BulkEmailContentPreviewResponse,
    ErrorResponse,
    FairEmailBatchDetailEnvelopeResponse,
    FairEmailBatchDetailResponse,
    FairEmailBatchListItemResponse,
    FairEmailBatchListResponse,
    FairEmailOutboxItemResponse,
    PreviewBulkEmailRequest,
    PreviewRecipientsRequest,
    RecipientPreviewItemResponse,
    RecipientPreviewSummaryResponse,
    SendBulkEmailRequest,
    SendBulkEmailResponse,
)
from app.modules.fair_emails.application.commands import (
    GetFairEmailBatchDetailQuery,
    ListFairEmailBatchesQuery,
    PreviewBulkEmailCommand,
    PreviewRecipientsQuery,
    SendBulkEmailCommand,
)
from app.modules.fair_emails.application.process_batch import process_fair_email_batch
from app.modules.fair_emails.domain.exceptions import (
    FairBulkEmailBatchNotFoundError,
    FairBulkEmailRecipientNotFoundError,
    FairNotEligibleForBulkEmailError,
)
from app.modules.fair_emails.domain.value_objects import RecipientOptions
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateAlreadyDeletedError,
    MailTemplateDefaultSmtpNotFoundError,
    MailTemplateInactiveForTestError,
    MailTemplateNotFoundError,
    MailTemplateRenderError,
)
from app.modules.smtp.domain.exceptions import SmtpAccountAlreadyDeletedError, SmtpAccountNotFoundError
from app.shared.background_jobs import run_blocking_background_task

router = APIRouter(prefix="/fairs/{fair_id}/bulk-email", tags=["fair-bulk-email"])
bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        return credentials.credentials
    from app.integrations.kyrox_core.dev_bypass import dev_bypass_enabled

    if dev_bypass_enabled():
        return get_settings().dev_bypass_token or "dev-bypass"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _to_recipient_options(body: PreviewRecipientsRequest | PreviewBulkEmailRequest | SendBulkEmailRequest) -> RecipientOptions:
    opts = body.recipient_options
    return RecipientOptions(
        include_customer_emails=opts.include_customer_emails,
        include_contact_emails=opts.include_contact_emails,
        skip_no_email=opts.skip_no_email,
        exclude_inactive=opts.exclude_inactive,
        dedupe_emails=opts.dedupe_emails,
    )


def _recipient_item(item) -> RecipientPreviewItemResponse:
    return RecipientPreviewItemResponse(
        recipient_key=item.recipient_key,
        recipient_name=item.recipient_name,
        company_name=item.company_name,
        email=item.email,
        source=item.source,
        customer_id=item.customer_id,
        contact_id=item.contact_id,
        participation_id=item.participation_id,
        status=item.status,
        skip_reason=item.skip_reason,
    )


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _batch_list_item(item) -> FairEmailBatchListItemResponse:
    return FairEmailBatchListItemResponse(
        id=item.id,
        status=item.status,
        template_id=item.template_id,
        template_name=item.template_name,
        smtp_account_id=item.smtp_account_id,
        smtp_account_name=item.smtp_account_name,
        subject=item.subject,
        total_recipients=item.total_recipients,
        queued_count=item.queued_count,
        sent_count=item.sent_count,
        failed_count=item.failed_count,
        skipped_count=item.skipped_count,
        created_at=_iso(item.created_at) or "",
        completed_at=_iso(item.completed_at),
    )


def _batch_detail(batch) -> FairEmailBatchDetailResponse:
    return FairEmailBatchDetailResponse(
        id=batch.id,
        fair_id=batch.fair_id,
        status=batch.status,
        template_id=batch.template_id,
        template_name=batch.template_name,
        smtp_account_id=batch.smtp_account_id,
        smtp_account_name=batch.smtp_account_name,
        subject=batch.subject,
        subject_override=batch.subject_override,
        total_recipients=batch.total_recipients,
        queued_count=batch.queued_count,
        sent_count=batch.sent_count,
        failed_count=batch.failed_count,
        skipped_count=batch.skipped_count,
        created_at=_iso(batch.created_at) or "",
        completed_at=_iso(batch.completed_at),
        created_by_user_id=batch.created_by_user_id,
    )


def _outbox_item(item) -> FairEmailOutboxItemResponse:
    return FairEmailOutboxItemResponse(
        id=item.id,
        recipient_email=item.recipient_email,
        recipient_name=item.recipient_name,
        company_name=item.company_name,
        recipient_source=item.recipient_source,
        customer_id=item.customer_id,
        contact_id=item.contact_id,
        status=item.status,
        error_message=item.error_message,
        attempts=item.attempts,
        sent_at=_iso(item.sent_at),
        created_at=_iso(item.created_at) or "",
        updated_at=_iso(item.updated_at) or "",
    )


@router.get(
    "/batches",
    response_model=FairEmailBatchListResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def list_email_batches(
    fair_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_list_email_batches_use_case),
) -> FairEmailBatchListResponse:
    try:
        result = use_case.execute(
            ListFairEmailBatchesQuery(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairNotEligibleForBulkEmailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FairEmailBatchListResponse(items=[_batch_list_item(item) for item in result.items])


@router.get(
    "/batches/{batch_id}",
    response_model=FairEmailBatchDetailEnvelopeResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_email_batch_detail(
    fair_id: UUID,
    batch_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_email_batch_detail_use_case),
) -> FairEmailBatchDetailEnvelopeResponse:
    try:
        result = use_case.execute(
            GetFairEmailBatchDetailQuery(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                batch_id=batch_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairBulkEmailBatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairNotEligibleForBulkEmailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FairEmailBatchDetailEnvelopeResponse(
        batch=_batch_detail(result.batch),
        items=[_outbox_item(item) for item in result.items],
    )


@router.post(
    "/preview-recipients",
    response_model=RecipientPreviewSummaryResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def preview_recipients(
    fair_id: UUID,
    body: PreviewRecipientsRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_preview_recipients_use_case),
) -> RecipientPreviewSummaryResponse:
    try:
        result = use_case.execute(
            PreviewRecipientsQuery(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                recipient_options=_to_recipient_options(body),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FairNotEligibleForBulkEmailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RecipientPreviewSummaryResponse(
        total_customers=result.total_customers,
        total_contacts=result.total_contacts,
        valid_email_count=result.valid_email_count,
        deduped_recipient_count=result.deduped_recipient_count,
        skipped_count=result.skipped_count,
        recipients=[_recipient_item(item) for item in result.recipients],
    )


@router.post(
    "/preview",
    response_model=BulkEmailContentPreviewResponse,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def preview_bulk_email(
    fair_id: UUID,
    body: PreviewBulkEmailRequest,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    use_case=Depends(get_preview_bulk_email_use_case),
) -> BulkEmailContentPreviewResponse:
    try:
        result = use_case.execute(
            PreviewBulkEmailCommand(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                template_id=body.template_id,
                sample_recipient_key=body.sample_recipient_key,
                subject_override=body.subject_override,
                recipient_options=_to_recipient_options(body),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MailTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        FairNotEligibleForBulkEmailError,
        FairBulkEmailRecipientNotFoundError,
        MailTemplateAlreadyDeletedError,
        MailTemplateInactiveForTestError,
        MailTemplateRenderError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return BulkEmailContentPreviewResponse(
        subject=result.subject,
        body_html=result.body_html,
        body_text=result.body_text,
        sample_recipient=_recipient_item(result.sample_recipient),
        total_send_count=result.total_send_count,
    )


@router.post(
    "/send",
    response_model=SendBulkEmailResponse,
    responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def send_bulk_email(
    fair_id: UUID,
    body: SendBulkEmailRequest,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    use_case=Depends(get_send_bulk_email_use_case),
) -> SendBulkEmailResponse:
    try:
        result = use_case.execute(
            SendBulkEmailCommand(
                organization_id=auth.organization_id,
                fair_id=fair_id,
                access_token=_access_token(credentials),
                user_id=auth.user_id,
                template_id=body.template_id,
                smtp_account_id=body.smtp_account_id,
                subject_override=body.subject_override,
                recipient_options=_to_recipient_options(body),
            )
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MailTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SmtpAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (
        FairNotEligibleForBulkEmailError,
        FairBulkEmailRecipientNotFoundError,
        MailTemplateAlreadyDeletedError,
        MailTemplateInactiveForTestError,
        MailTemplateDefaultSmtpNotFoundError,
        SmtpAccountAlreadyDeletedError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    background_tasks.add_task(
        run_blocking_background_task,
        process_fair_email_batch,
        result.batch_id,
        auth.organization_id,
    )

    return SendBulkEmailResponse(
        batch_id=result.batch_id,
        status=result.status,
        total_count=result.total_count,
        skipped_count=result.skipped_count,
        message=result.message,
    )
