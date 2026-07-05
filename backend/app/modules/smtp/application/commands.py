from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.modules.smtp.domain.value_objects import SmtpEncryptionType


@dataclass(frozen=True)
class CreateSmtpAccountCommand:
    organization_id: UUID
    access_token: str
    user_id: UUID
    name: str
    from_email: str
    host: str
    port: int
    from_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    encryption_type: str | SmtpEncryptionType = SmtpEncryptionType.STARTTLS
    is_default: bool = False
    is_active: bool = True


@dataclass(frozen=True)
class UpdateSmtpAccountCommand:
    organization_id: UUID
    account_id: UUID
    access_token: str
    user_id: UUID
    name: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    encryption_type: str | SmtpEncryptionType | None = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


@dataclass(frozen=True)
class GetSmtpAccountQuery:
    organization_id: UUID
    account_id: UUID


@dataclass(frozen=True)
class ListSmtpAccountsQuery:
    organization_id: UUID


@dataclass(frozen=True)
class SetDefaultSmtpAccountCommand:
    organization_id: UUID
    account_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class DeleteSmtpAccountCommand:
    organization_id: UUID
    account_id: UUID
    access_token: str
    user_id: UUID


@dataclass(frozen=True)
class SmtpAccountResult:
    id: UUID
    organization_id: UUID
    name: str
    from_email: str
    from_name: Optional[str]
    host: str
    port: int
    username: Optional[str]
    encryption_type: SmtpEncryptionType
    is_default: bool
    is_active: bool
    has_password: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


@dataclass(frozen=True)
class SmtpAccountListResult:
    items: list[SmtpAccountResult]
