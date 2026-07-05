from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.smtp.application.commands import SetDefaultSmtpAccountCommand, SmtpAccountResult
from app.modules.smtp.application.mappers import smtp_account_to_result
from app.modules.smtp.domain.exceptions import SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_UPDATE = "fair_crm.smtp.update"


class SetDefaultSmtpAccountUseCase:
    def __init__(
        self,
        repository: SmtpAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: SetDefaultSmtpAccountCommand) -> SmtpAccountResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        account = self._repository.get_by_id(command.organization_id, command.account_id)
        if account is None:
            raise SmtpAccountNotFoundError("SMTP account not found")

        now = datetime.now(tz=UTC)
        self._repository.clear_default_for_organization(
            command.organization_id,
            exclude_account_id=account.id,
        )
        account.mark_as_default(now=now)
        saved = self._repository.update(account)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.smtp_account.set_default",
            resource_type="smtp_account",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        return smtp_account_to_result(saved)
