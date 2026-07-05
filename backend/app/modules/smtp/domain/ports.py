from typing import Protocol
from uuid import UUID

from app.modules.smtp.domain.entities import SmtpAccount


class SmtpAccountRepository(Protocol):
    def add(self, account: SmtpAccount) -> SmtpAccount: ...

    def update(self, account: SmtpAccount) -> SmtpAccount: ...

    def get_by_id(self, organization_id: UUID, account_id: UUID) -> SmtpAccount | None: ...

    def list_by_organization(self, organization_id: UUID) -> list[SmtpAccount]: ...

    def get_default_for_organization(self, organization_id: UUID) -> SmtpAccount | None: ...

    def clear_default_for_organization(
        self,
        organization_id: UUID,
        *,
        exclude_account_id: UUID | None = None,
    ) -> None: ...
