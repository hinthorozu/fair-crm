from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.smtp.application.commands import DeleteSmtpAccountCommand, SmtpAccountResult
from app.modules.smtp.application.mappers import smtp_account_to_result
from app.modules.smtp.domain.exceptions import SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_DELETE = "fair_crm.smtp.delete"


class DeleteSmtpAccountUseCase:
    def __init__(
        self,
        repository: SmtpAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: DeleteSmtpAccountCommand) -> SmtpAccountResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        account = self._repository.get_by_id(command.organization_id, command.account_id)
        if account is None:
            raise SmtpAccountNotFoundError("SMTP account not found")

        now = datetime.now(tz=UTC)
        account.soft_delete(now=now)
        saved = self._repository.update(account)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.smtp_account.deleted",
            resource_type="smtp_account",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        return smtp_account_to_result(saved)
