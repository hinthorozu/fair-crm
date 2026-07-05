from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.auth import AuthContext
from app.integrations.kyrox_core.client import HttpAuditAdapter, HttpAuthorizationAdapter
from app.integrations.kyrox_core.dev_bypass import (
    AllowAllAuthorizationAdapter,
    NoOpAuditAdapter,
    dev_bypass_enabled,
    resolve_auth_context,
)
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fair_emails.application.fair_bulk_mail_operation_sync import FairBulkEmailMailOperationSync
from app.modules.fair_emails.application.get_email_batch_detail import GetFairEmailBatchDetailUseCase
from app.modules.fair_emails.application.list_email_batches import ListFairEmailBatchesUseCase
from app.modules.fair_emails.application.preview_bulk_email import PreviewFairBulkEmailUseCase
from app.modules.fair_emails.application.preview_recipients import PreviewFairEmailRecipientsUseCase
from app.modules.fair_emails.application.recipient_service import FairBulkEmailRecipientService
from app.modules.fair_emails.application.send_bulk_email import SendFairBulkEmailUseCase
from app.modules.fair_emails.infrastructure.recipient_loader import FairBulkEmailRecipientLoader
from app.modules.fair_emails.infrastructure.repositories.fair_email_batch_repository import (
    SqlAlchemyFairEmailBatchRepository,
)
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
    SqlAlchemyMailTemplateRepository,
)
from app.modules.mail_templates.infrastructure.template_renderer import JinjaMailTemplateRenderer
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import SqlAlchemySmtpAccountRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_authorization_adapter() -> AuthorizationPort:
    if dev_bypass_enabled():
        return AllowAllAuthorizationAdapter()
    return HttpAuthorizationAdapter()


def get_audit_adapter() -> HttpAuditAdapter | NoOpAuditAdapter:
    if dev_bypass_enabled():
        return NoOpAuditAdapter()
    return HttpAuditAdapter()


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    organization_id: UUID = Header(..., alias="X-Organization-Id"),
    dev_user_id: UUID | None = Header(default=None, alias="X-Dev-User-Id"),
) -> AuthContext:
    try:
        return resolve_auth_context(credentials, organization_id, dev_user_id=dev_user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc


def get_preview_recipients_use_case(
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> PreviewFairEmailRecipientsUseCase:
    return PreviewFairEmailRecipientsUseCase(
        SqlAlchemyFairRepository(db),
        FairBulkEmailRecipientService(db),
        authorization,
    )


def get_preview_bulk_email_use_case(
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> PreviewFairBulkEmailUseCase:
    return PreviewFairBulkEmailUseCase(
        SqlAlchemyFairRepository(db),
        SqlAlchemyMailTemplateRepository(db),
        JinjaMailTemplateRenderer(),
        FairBulkEmailRecipientService(db),
        FairBulkEmailRecipientLoader(db),
        authorization,
    )


def get_send_bulk_email_use_case(
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> SendFairBulkEmailUseCase:
    return SendFairBulkEmailUseCase(
        SqlAlchemyFairRepository(db),
        SqlAlchemyMailTemplateRepository(db),
        SqlAlchemySmtpAccountRepository(db),
        SqlAlchemyFairEmailBatchRepository(db),
        FairBulkEmailRecipientService(db),
        FairBulkEmailMailOperationSync(db),
        authorization,
        audit,
    )


def get_list_email_batches_use_case(
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> ListFairEmailBatchesUseCase:
    return ListFairEmailBatchesUseCase(
        SqlAlchemyFairRepository(db),
        SqlAlchemyFairEmailBatchRepository(db),
        SqlAlchemyMailTemplateRepository(db),
        SqlAlchemySmtpAccountRepository(db),
        authorization,
    )


def get_email_batch_detail_use_case(
    db: Session = Depends(get_db),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
) -> GetFairEmailBatchDetailUseCase:
    return GetFairEmailBatchDetailUseCase(
        SqlAlchemyFairRepository(db),
        SqlAlchemyFairEmailBatchRepository(db),
        SqlAlchemyMailTemplateRepository(db),
        SqlAlchemySmtpAccountRepository(db),
        authorization,
    )
