from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ListMailSendOperationsQuery:
    organization_id: UUID
    user_id: UUID
    access_token: str
    search: str | None = None
    status: str | None = None
    source_type: str | None = None
    smtp_account_id: UUID | None = None
    fair_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True)
class RetryMailSendOperationCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    operation_id: UUID
