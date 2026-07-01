from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.contacts.domain.exceptions import (
    ContactAlreadyDeletedError,
    InvalidContactEmailError,
    InvalidContactNameError,
)
from app.modules.contacts.domain.services.normalizers import normalize_email_list, normalize_phone


def _normalize_and_validate_email(email: Optional[str]) -> Optional[str]:
    if email is None:
        return None
    try:
        return normalize_email_list(email)
    except ValueError as exc:
        raise InvalidContactEmailError(str(exc)) from exc


@dataclass
class Contact:
    id: UUID
    organization_id: UUID
    customer_id: UUID
    first_name: str
    last_name: str
    title: Optional[str]
    department: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    mobile_phone: Optional[str]
    linkedin: Optional[str]
    notes: Optional[str]
    is_primary: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        customer_id: UUID,
        first_name: str,
        last_name: str,
        title: Optional[str] = None,
        department: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        mobile_phone: Optional[str] = None,
        linkedin: Optional[str] = None,
        notes: Optional[str] = None,
        is_primary: bool = False,
        is_active: bool = True,
        now: datetime,
    ) -> "Contact":
        trimmed_first = first_name.strip()
        trimmed_last = last_name.strip()
        if not trimmed_first:
            raise InvalidContactNameError("first_name must not be empty")
        if not trimmed_last:
            raise InvalidContactNameError("last_name must not be empty")

        normalized_email = _normalize_and_validate_email(email)

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            first_name=trimmed_first,
            last_name=trimmed_last,
            title=title.strip() if title else None,
            department=department.strip() if department else None,
            email=normalized_email,
            phone=normalize_phone(phone) if phone else None,
            mobile_phone=normalize_phone(mobile_phone) if mobile_phone else None,
            linkedin=linkedin.strip() if linkedin else None,
            notes=notes.strip() if notes else None,
            is_primary=is_primary,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    def ensure_mutable(self) -> None:
        if self.deleted_at is not None:
            raise ContactAlreadyDeletedError("Contact is deleted")

    def update_fields(
        self,
        *,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        title: Optional[str] = None,
        department: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        mobile_phone: Optional[str] = None,
        linkedin: Optional[str] = None,
        notes: Optional[str] = None,
        is_primary: Optional[bool] = None,
        is_active: Optional[bool] = None,
        now: datetime,
    ) -> None:
        self.ensure_mutable()

        if first_name is not None:
            trimmed = first_name.strip()
            if not trimmed:
                raise InvalidContactNameError("first_name must not be empty")
            self.first_name = trimmed

        if last_name is not None:
            trimmed = last_name.strip()
            if not trimmed:
                raise InvalidContactNameError("last_name must not be empty")
            self.last_name = trimmed

        if title is not None:
            self.title = title.strip() if title else None
        if department is not None:
            self.department = department.strip() if department else None
        if email is not None:
            self.email = _normalize_and_validate_email(email if email else None)
        if phone is not None:
            self.phone = normalize_phone(phone) if phone else None
        if mobile_phone is not None:
            self.mobile_phone = normalize_phone(mobile_phone) if mobile_phone else None
        if linkedin is not None:
            self.linkedin = linkedin.strip() if linkedin else None
        if notes is not None:
            self.notes = notes.strip() if notes else None
        if is_primary is not None:
            self.is_primary = is_primary
        if is_active is not None:
            self.is_active = is_active

        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        if self.deleted_at is not None:
            return
        self.deleted_at = now
        self.is_active = False
        self.is_primary = False
        self.updated_at = now
