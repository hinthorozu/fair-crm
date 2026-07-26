"""Email-accounts API dependencies."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.dev_bypass import NoOpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.email_accounts.application.create_provider_account import CreateProviderAccountUseCase
from app.modules.email_accounts.application.manage_email_accounts import (
    DeleteEmailAccountUseCase,
    GetEmailAccountUseCase,
    ListEmailAccountsUseCase,
    SendTestEmailAccountMailUseCase,
    SetDefaultEmailAccountUseCase,
)
from app.modules.email_accounts.application.update_provider_account import UpdateProviderAccountUseCase
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.mail_send_operations.application.mail_send_operation_service import (
    MailSendOperationService,
)
from app.modules.smtp.api.dependencies import (  # noqa: F401
    PERMISSION_READ,
    get_audit_adapter,
    get_auth_context,
    get_authorization_adapter,
    get_create_smtp_account_use_case,
    get_mail_send_operation_service,
    get_update_smtp_account_use_case,
    require_read_permission,
)
from app.modules.smtp.application.create_smtp_account import CreateSmtpAccountUseCase
from app.modules.smtp.application.update_smtp_account import UpdateSmtpAccountUseCase

get_create_email_account_use_case = get_create_smtp_account_use_case
get_update_email_account_use_case = get_update_smtp_account_use_case


def get_email_account_repository(db: Session = Depends(get_db)) -> SqlAlchemyEmailAccountRepository:
    return SqlAlchemyEmailAccountRepository(db)


def get_list_email_accounts_unified_use_case(
    repository: SqlAlchemyEmailAccountRepository = Depends(get_email_account_repository),
) -> ListEmailAccountsUseCase:
    return ListEmailAccountsUseCase(repository)


def get_get_email_account_unified_use_case(
    repository: SqlAlchemyEmailAccountRepository = Depends(get_email_account_repository),
) -> GetEmailAccountUseCase:
    return GetEmailAccountUseCase(repository)


def get_create_provider_account_use_case(
    repository: SqlAlchemyEmailAccountRepository = Depends(get_email_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> CreateProviderAccountUseCase:
    return CreateProviderAccountUseCase(repository, authorization, audit)


def get_update_provider_account_use_case(
    repository: SqlAlchemyEmailAccountRepository = Depends(get_email_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> UpdateProviderAccountUseCase:
    return UpdateProviderAccountUseCase(repository, authorization, audit)


def get_set_default_email_account_unified_use_case(
    repository: SqlAlchemyEmailAccountRepository = Depends(get_email_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> SetDefaultEmailAccountUseCase:
    return SetDefaultEmailAccountUseCase(repository, authorization, audit)


def get_delete_email_account_unified_use_case(
    repository: SqlAlchemyEmailAccountRepository = Depends(get_email_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
) -> DeleteEmailAccountUseCase:
    return DeleteEmailAccountUseCase(repository, authorization, audit)


def get_send_test_email_account_unified_use_case(
    repository: SqlAlchemyEmailAccountRepository = Depends(get_email_account_repository),
    authorization: AuthorizationPort = Depends(get_authorization_adapter),
    audit: HttpAuditAdapter | NoOpAuditAdapter = Depends(get_audit_adapter),
    mail_send_operations: MailSendOperationService = Depends(get_mail_send_operation_service),
    db: Session = Depends(get_db),
) -> SendTestEmailAccountMailUseCase:
    return SendTestEmailAccountMailUseCase(
        repository,
        authorization,
        audit,
        mail_send_operations,
        db,
    )


# Keep CreateSmtpAccountUseCase type export for routes typing.
__all__ = [
    "CreateSmtpAccountUseCase",
    "UpdateSmtpAccountUseCase",
    "PERMISSION_READ",
    "get_auth_context",
    "require_read_permission",
]
