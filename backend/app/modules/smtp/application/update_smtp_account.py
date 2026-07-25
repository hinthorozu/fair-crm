from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.smtp.application.commands import SmtpAccountResult, UpdateSmtpAccountCommand
from app.modules.smtp.application.mappers import smtp_account_to_result
from app.modules.smtp.domain.exceptions import SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository

PERMISSION_UPDATE = "fair_crm.email_accounts.update"


class UpdateSmtpAccountUseCase:
    def __init__(
        self,
        repository: SmtpAccountRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateSmtpAccountCommand) -> SmtpAccountResult:
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
        password_update = command.password
        if password_update is not None and password_update == "":
            password_update = None

        will_deactivate = command.is_active is False and account.is_active
        if account.is_default and will_deactivate:
            self._repository.promote_next_active_default(
                command.organization_id,
                exclude_account_id=account.id,
                now=now,
            )

        is_default = command.is_default
        if will_deactivate:
            # Deactivating a default account always clears is_default on current.
            is_default = False

        account.update_fields(
            name=command.name,
            from_email=command.from_email,
            from_name=command.from_name,
            host=command.host,
            port=command.port,
            username=command.username,
            password=password_update,
            encryption_type=command.encryption_type,
            is_default=is_default,
            is_active=command.is_active,
            now=now,
        )

        if is_default is True:
            # Flush cleared defaults before writing this account as default.
            self._repository.clear_default_for_organization(
                command.organization_id,
                exclude_account_id=account.id,
            )
            self._repository.flush()

        saved = self._repository.update(account)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.email_account.updated",
            resource_type="email_account",
            resource_id=str(saved.id),
            new_values={"name": saved.name},
            metadata={"user_id": str(command.user_id)},
        )

        return smtp_account_to_result(saved)
