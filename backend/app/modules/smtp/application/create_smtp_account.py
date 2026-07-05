from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.smtp.application.commands import CreateSmtpAccountCommand, SmtpAccountResult
from app.modules.smtp.application.mappers import smtp_account_to_result
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_CREATE = "fair_crm.smtp.create"


class CreateSmtpAccountUseCase:
    def __init__(
        self,
        repository: SmtpAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateSmtpAccountCommand) -> SmtpAccountResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        existing_accounts = self._repository.list_by_organization(command.organization_id)
        should_be_default = command.is_default or len(existing_accounts) == 0

        if should_be_default:
            self._repository.clear_default_for_organization(command.organization_id)

        now = datetime.now(tz=UTC)
        account = SmtpAccount.create(
            organization_id=command.organization_id,
            name=command.name,
            from_email=command.from_email,
            host=command.host,
            port=command.port,
            from_name=command.from_name,
            username=command.username,
            password=command.password,
            encryption_type=command.encryption_type,
            is_default=should_be_default,
            is_active=command.is_active,
            now=now,
        )
        saved = self._repository.add(account)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.smtp_account.created",
            resource_type="smtp_account",
            resource_id=str(saved.id),
            new_values={"name": saved.name, "from_email": saved.from_email},
            metadata={"user_id": str(command.user_id)},
        )

        return smtp_account_to_result(saved)
