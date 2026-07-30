"""Email account aggregate — shared account identity plus optional SMTP config."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.email_accounts.domain.exceptions import (
    EmailAccountAlreadyDeletedError,
    EmailAccountNotDefaultEligibleError,
    UnsupportedEmailAccountTypeError,
)
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.shared.email import sanitize_scraped_email

_ALLOWED_ENCRYPTION_TYPES = frozenset({"none", "ssl", "tls", "starttls"})
_MIN_DELIVERY_ATTEMPTS = 1
_MAX_DELIVERY_ATTEMPTS = 5
_DEFAULT_DELIVERY_ATTEMPTS = 3


def _validate_max_delivery_attempts(value: int) -> int:
    if value < _MIN_DELIVERY_ATTEMPTS or value > _MAX_DELIVERY_ATTEMPTS:
        raise ValueError(
            f"max_delivery_attempts must be between {_MIN_DELIVERY_ATTEMPTS} and {_MAX_DELIVERY_ATTEMPTS}"
        )
    return value


def _validate_port(port: int) -> int:
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    return port


def _normalize_encryption_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _ALLOWED_ENCRYPTION_TYPES:
        raise ValueError(
            f"encryption_type must be one of: {', '.join(sorted(_ALLOWED_ENCRYPTION_TYPES))}"
        )
    return normalized


def _normalize_account_type(value: str | EmailAccountType) -> EmailAccountType:
    if isinstance(value, EmailAccountType):
        return value
    try:
        return EmailAccountType(value.strip().lower())
    except ValueError as exc:
        raise UnsupportedEmailAccountTypeError(
            f"account_type must be one of: {', '.join(item.value for item in EmailAccountType)}"
        ) from exc


@dataclass
class EmailAccount:
    id: UUID
    organization_id: UUID
    name: str
    account_type: EmailAccountType
    provider_key: Optional[str]
    from_email: str
    from_name: Optional[str]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    max_delivery_attempts: int = _DEFAULT_DELIVERY_ATTEMPTS

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        name: str,
        from_email: str,
        account_type: str | EmailAccountType = EmailAccountType.SMTP,
        provider_key: Optional[str] = None,
        from_name: Optional[str] = None,
        is_default: bool = False,
        is_active: bool = True,
        max_delivery_attempts: int = _DEFAULT_DELIVERY_ATTEMPTS,
        now: datetime,
    ) -> EmailAccount:
        trimmed_name = name.strip()
        if not trimmed_name:
            raise ValueError("name must not be empty")

        cleaned_email = sanitize_scraped_email(from_email)
        if cleaned_email is None:
            raise ValueError("from_email must be a valid email address")

        resolved_type = _normalize_account_type(account_type)
        trimmed_provider_key = provider_key.strip() if provider_key else None

        if resolved_type == EmailAccountType.SMTP:
            if trimmed_provider_key is not None:
                raise ValueError("provider_key must be None for smtp accounts")
        elif resolved_type == EmailAccountType.PROVIDER:
            if not trimmed_provider_key:
                raise ValueError("provider_key is required for provider accounts")
        else:
            raise UnsupportedEmailAccountTypeError(
                f"Unsupported account_type: {resolved_type}"
            )

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            name=trimmed_name,
            account_type=resolved_type,
            provider_key=trimmed_provider_key,
            from_email=cleaned_email,
            from_name=from_name.strip() if from_name else None,
            is_default=is_default,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            max_delivery_attempts=_validate_max_delivery_attempts(max_delivery_attempts),
        )

    def ensure_mutable(self) -> None:
        if self.deleted_at is not None:
            raise EmailAccountAlreadyDeletedError("Email account is deleted")

    def ensure_default_eligible(self) -> None:
        self.ensure_mutable()
        if not self.is_active:
            raise EmailAccountNotDefaultEligibleError(
                "Inactive email account cannot be default"
            )

    def mark_as_default(self, *, now: datetime) -> None:
        self.ensure_default_eligible()
        self.is_default = True
        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        if self.deleted_at is not None:
            return
        self.deleted_at = now
        self.is_active = False
        self.is_default = False
        self.updated_at = now

    def update_common_fields(
        self,
        *,
        name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        provider_key: Optional[str] = None,
        is_default: Optional[bool] = None,
        is_active: Optional[bool] = None,
        max_delivery_attempts: Optional[int] = None,
        now: datetime,
    ) -> None:
        self.ensure_mutable()

        if name is not None:
            trimmed = name.strip()
            if not trimmed:
                raise ValueError("name must not be empty")
            self.name = trimmed

        if from_email is not None:
            cleaned = sanitize_scraped_email(from_email)
            if cleaned is None:
                raise ValueError("from_email must be a valid email address")
            self.from_email = cleaned

        if from_name is not None:
            self.from_name = from_name.strip() if from_name else None

        if provider_key is not None:
            trimmed = provider_key.strip() if provider_key else None
            if self.account_type == EmailAccountType.SMTP:
                if trimmed is not None:
                    raise ValueError("provider_key must be None for smtp accounts")
                self.provider_key = None
            elif self.account_type == EmailAccountType.PROVIDER:
                if not trimmed:
                    raise ValueError("provider_key is required for provider accounts")
                self.provider_key = trimmed
            else:
                raise UnsupportedEmailAccountTypeError(
                    f"Unsupported account_type: {self.account_type}"
                )

        if is_default is not None:
            self.is_default = is_default

        if is_active is not None:
            self.is_active = is_active

        if max_delivery_attempts is not None:
            self.max_delivery_attempts = _validate_max_delivery_attempts(max_delivery_attempts)

        self.updated_at = now


@dataclass
class EmailAccountSmtpConfig:
    email_account_id: UUID
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    encryption_type: str

    @classmethod
    def create(
        cls,
        *,
        email_account_id: UUID,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        encryption_type: str = "starttls",
    ) -> EmailAccountSmtpConfig:
        trimmed_host = host.strip()
        if not trimmed_host:
            raise ValueError("host must not be empty")

        return cls(
            email_account_id=email_account_id,
            host=trimmed_host,
            port=_validate_port(port),
            username=username.strip() if username else None,
            password=password,
            encryption_type=_normalize_encryption_type(encryption_type),
        )

    def update(
        self,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        encryption_type: Optional[str] = None,
    ) -> None:
        if host is not None:
            trimmed = host.strip()
            if not trimmed:
                raise ValueError("host must not be empty")
            self.host = trimmed

        if port is not None:
            self.port = _validate_port(port)

        if username is not None:
            self.username = username.strip() if username else None

        if password is not None:
            self.password = password

        if encryption_type is not None:
            self.encryption_type = _normalize_encryption_type(encryption_type)
