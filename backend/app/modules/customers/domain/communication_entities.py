from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CustomerPhone:
    id: UUID
    customer_id: UUID
    phone: str
    is_primary: bool
    created_at: datetime


@dataclass(frozen=True)
class CustomerEmail:
    id: UUID
    customer_id: UUID
    email: str
    is_primary: bool
    created_at: datetime


@dataclass(frozen=True)
class CustomerWebsite:
    id: UUID
    customer_id: UUID
    website: str
    is_primary: bool
    created_at: datetime


@dataclass(frozen=True)
class CustomerCommunications:
    phones: list[CustomerPhone]
    emails: list[CustomerEmail]
    websites: list[CustomerWebsite]


@dataclass(frozen=True)
class CustomerCommunicationListSummary:
    phone: str | None = None
    phone_extra_count: int = 0
    email: str | None = None
    email_extra_count: int = 0
    website: str | None = None
    website_extra_count: int = 0
