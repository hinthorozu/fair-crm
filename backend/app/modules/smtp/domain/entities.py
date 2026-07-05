"""SMTP account aggregate — one record per tenant (organization) outbound mail configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.smtp.domain.exceptions import (
    InvalidSmtpAccountEmailError,
    InvalidSmtpAccountHostError,
    InvalidSmtpAccountNameError,
    InvalidSmtpAccountPortError,
    InvalidSmtpEncryptionTypeError,
    SmtpAccountAlreadyDeletedError,
    SmtpAccountNotDefaultEligibleError,
)
from app.modules.smtp.domain.value_objects import SmtpEncryptionType


def _normalize_encryption_type(value: str | SmtpEncryptionType) -> SmtpEncryptionType:
    if isinstance(value, SmtpEncryptionType):
        return value
    normalized = value.strip().lower()
    try:
        return SmtpEncryptionType(normalized)
    except ValueError as exc:
        raise InvalidSmtpEncryptionTypeError(
            f"encryption_type must be one of: {', '.join(item.value for item in SmtpEncryptionType)}"
        ) from exc


def _validate_port(port: int) -> int:
    if port < 1 or port > 65535:
        raise InvalidSmtpAccountPortError("port must be between 1 and 65535")
    return port


@dataclass
class SmtpAccount:
    id: UUID
    organization_id: UUID
    name: str
    from_email: str
    from_name: Optional[str]
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    encryption_type: SmtpEncryptionType
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        name: str,
        from_email: str,
        host: str,
        port: int,
        from_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        encryption_type: str | SmtpEncryptionType = SmtpEncryptionType.STARTTLS,
        is_default: bool = False,
        is_active: bool = True,
        now: datetime,
    ) -> SmtpAccount:
        trimmed_name = name.strip()
        if not trimmed_name:
            raise InvalidSmtpAccountNameError("name must not be empty")

        trimmed_email = from_email.strip()
        if not trimmed_email or "@" not in trimmed_email:
            raise InvalidSmtpAccountEmailError("from_email must be a valid email address")

        trimmed_host = host.strip()
        if not trimmed_host:
            raise InvalidSmtpAccountHostError("host must not be empty")

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            name=trimmed_name,
            from_email=trimmed_email,
            from_name=from_name.strip() if from_name else None,
            host=trimmed_host,
            port=_validate_port(port),
            username=username.strip() if username else None,
            password=password,
            encryption_type=_normalize_encryption_type(encryption_type),
            is_default=is_default,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    def ensure_mutable(self) -> None:
        if self.deleted_at is not None:
            raise SmtpAccountAlreadyDeletedError("SMTP account is deleted")

    def update_fields(
        self,
        *,
        name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        encryption_type: str | SmtpEncryptionType | None = None,
        is_default: Optional[bool] = None,
        is_active: Optional[bool] = None,
        now: datetime,
    ) -> None:
        self.ensure_mutable()

        if name is not None:
            trimmed = name.strip()
            if not trimmed:
                raise InvalidSmtpAccountNameError("name must not be empty")
            self.name = trimmed

        if from_email is not None:
            trimmed = from_email.strip()
            if not trimmed or "@" not in trimmed:
                raise InvalidSmtpAccountEmailError("from_email must be a valid email address")
            self.from_email = trimmed

        if from_name is not None:
            self.from_name = from_name.strip() if from_name else None

        if host is not None:
            trimmed = host.strip()
            if not trimmed:
                raise InvalidSmtpAccountHostError("host must not be empty")
            self.host = trimmed

        if port is not None:
            self.port = _validate_port(port)

        if username is not None:
            self.username = username.strip() if username else None

        if password is not None:
            self.password = password

        if encryption_type is not None:
            self.encryption_type = _normalize_encryption_type(encryption_type)

        if is_default is not None:
            self.is_default = is_default

        if is_active is not None:
            self.is_active = is_active

        self.updated_at = now

    def ensure_default_eligible(self) -> None:
        self.ensure_mutable()
        if not self.is_active:
            raise SmtpAccountNotDefaultEligibleError("Inactive SMTP account cannot be default")

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
