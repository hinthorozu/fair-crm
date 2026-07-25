from typing import Protocol
from uuid import UUID

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig


class EmailAccountRepository(Protocol):
    def add_smtp_account(
        self,
        account: EmailAccount,
        smtp_config: EmailAccountSmtpConfig,
    ) -> tuple[EmailAccount, EmailAccountSmtpConfig]: ...

    def update_smtp_account(
        self,
        account: EmailAccount,
        smtp_config: EmailAccountSmtpConfig,
    ) -> tuple[EmailAccount, EmailAccountSmtpConfig]: ...

    def get_by_id(
        self,
        organization_id: UUID,
        account_id: UUID,
    ) -> EmailAccount | None: ...

    def get_smtp_config(self, account_id: UUID) -> EmailAccountSmtpConfig | None: ...

    def get_with_smtp_config(
        self,
        organization_id: UUID,
        account_id: UUID,
    ) -> tuple[EmailAccount, EmailAccountSmtpConfig] | None: ...

    def list_by_organization(self, organization_id: UUID) -> list[EmailAccount]: ...

    def list_active_accounts(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID | None = None,
    ) -> list[EmailAccount]: ...

    def list_smtp_by_organization(
        self,
        organization_id: UUID,
    ) -> list[tuple[EmailAccount, EmailAccountSmtpConfig]]: ...

    def get_default_for_organization(self, organization_id: UUID) -> EmailAccount | None: ...

    def clear_default_for_organization(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID | None = None,
    ) -> None: ...

    def update_account(self, account: EmailAccount) -> EmailAccount: ...

    def flush(self) -> None: ...
