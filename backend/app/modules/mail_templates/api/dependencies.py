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
from app.modules.mail_templates.application.create_mail_template import CreateMailTemplateUseCase
from app.modules.mail_templates.application.delete_mail_template import DeleteMailTemplateUseCase
from app.modules.mail_templates.application.get_mail_template import GetMailTemplateUseCase
from app.modules.mail_templates.application.list_mail_templates import ListMailTemplatesUseCase
from app.modules.mail_templates.application.render_mail_template import RenderMailTemplateUseCase
from app.modules.mail_templates.application.send_test_mail_template import SendTestMailTemplateUseCase
from app.modules.mail_templates.application.update_mail_template import UpdateMailTemplateUseCase
from app.modules.mail_send_operations.application.mail_send_operation_service import MailSendOperationService
from app.modules.mail_send_operations.infrastructure.repositories.mail_send_operation_repository import (
    SqlAlchemyMailSendOperationRepository,
)
from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
    SqlAlchemyMailTemplateRepository,
)
from app.modules.mail_templates.infrastructure.template_renderer import JinjaMailTemplateRenderer
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import SqlAlchemySmtpAccountRepository

bearer_scheme = HTTPBearer(auto_error=False)

PERMISSION_READ = "fair_crm.mail_templates.read"


def get_mail_template_repository(db: Session = Depends(get_db)) -> SqlAlchemyMailTemplateRepository:
    return SqlAlchemyMailTemplateRepository(db)


def get_template_renderer() -> JinjaMailTemplateRenderer:
    return JinjaMailTemplateRenderer()


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


def require_read_permission(
    auth: AuthContext = Depends(get_auth_context),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    if dev_bypass_enabled():
        return auth
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not authorization.check_permission(
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        permission_code=PERMISSION_READ,
        access_token=credentials.credentials,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return auth


def get_create_mail_template_use_case(
    repository: SqlAlchemyMailTemplateRepository = Depends(get_mail_template_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateMailTemplateUseCase:
    return CreateMailTemplateUseCase(repository, authorization, audit)


def get_update_mail_template_use_case(
    repository: SqlAlchemyMailTemplateRepository = Depends(get_mail_template_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateMailTemplateUseCase:
    return UpdateMailTemplateUseCase(repository, authorization, audit)


def get_get_mail_template_use_case(
    repository: SqlAlchemyMailTemplateRepository = Depends(get_mail_template_repository),
) -> GetMailTemplateUseCase:
    return GetMailTemplateUseCase(repository)


def get_list_mail_templates_use_case(
    repository: SqlAlchemyMailTemplateRepository = Depends(get_mail_template_repository),
) -> ListMailTemplatesUseCase:
    return ListMailTemplatesUseCase(repository)


def get_delete_mail_template_use_case(
    repository: SqlAlchemyMailTemplateRepository = Depends(get_mail_template_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> DeleteMailTemplateUseCase:
    return DeleteMailTemplateUseCase(repository, authorization, audit)


def get_render_mail_template_use_case(
    repository: SqlAlchemyMailTemplateRepository = Depends(get_mail_template_repository),
    renderer: JinjaMailTemplateRenderer = Depends(get_template_renderer),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> RenderMailTemplateUseCase:
    return RenderMailTemplateUseCase(repository, renderer, authorization, audit)


def get_smtp_account_repository(db: Session = Depends(get_db)) -> SqlAlchemySmtpAccountRepository:
    return SqlAlchemySmtpAccountRepository(db)


def get_mail_send_operation_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyMailSendOperationRepository:
    return SqlAlchemyMailSendOperationRepository(db)


def get_mail_send_operation_service(
    repository: SqlAlchemyMailSendOperationRepository = Depends(get_mail_send_operation_repository),
) -> MailSendOperationService:
    return MailSendOperationService(repository)


def get_send_test_mail_template_use_case(
    repository: SqlAlchemyMailTemplateRepository = Depends(get_mail_template_repository),
    smtp_repository: SqlAlchemySmtpAccountRepository = Depends(get_smtp_account_repository),
    renderer: JinjaMailTemplateRenderer = Depends(get_template_renderer),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
    mail_send_operations: MailSendOperationService = Depends(get_mail_send_operation_service),
) -> SendTestMailTemplateUseCase:
    return SendTestMailTemplateUseCase(
        repository,
        smtp_repository,
        renderer,
        authorization,
        audit,
        mail_send_operations,
    )
