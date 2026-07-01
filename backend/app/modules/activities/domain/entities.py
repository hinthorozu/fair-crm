from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.activities.domain.exceptions import (
    ActivityAlreadyDeletedError,
    InvalidActivitySourceError,
    InvalidActivityStatusError,
    InvalidActivitySubjectError,
    InvalidActivityTypeError,
)
from app.modules.activities.domain.value_objects import (
    ActivitySource,
    ActivityStatus,
    ActivityType,
)


def _validate_type(value: str) -> str:
    try:
        return ActivityType(value)
    except ValueError as exc:
        raise InvalidActivityTypeError(f"Invalid activity type: {value}") from exc


def _validate_status(value: str) -> str:
    try:
        return ActivityStatus(value)
    except ValueError as exc:
        raise InvalidActivityStatusError(f"Invalid activity status: {value}") from exc


def _validate_source(value: str) -> str:
    try:
        return ActivitySource(value)
    except ValueError as exc:
        raise InvalidActivitySourceError(f"Invalid activity source: {value}") from exc


@dataclass
class Activity:
    id: UUID
    organization_id: UUID
    customer_id: UUID
    contact_id: Optional[UUID]
    activity_type: str
    subject: str
    description: Optional[str]
    activity_date: datetime
    follow_up_date: Optional[datetime]
    status: str
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        customer_id: UUID,
        contact_id: Optional[UUID] = None,
        activity_type: str,
        subject: str,
        description: Optional[str] = None,
        activity_date: datetime,
        follow_up_date: Optional[datetime] = None,
        status: str,
        source: str = ActivitySource.MANUAL,
        is_active: bool = True,
        now: datetime,
    ) -> "Activity":
        trimmed_subject = subject.strip()
        if not trimmed_subject:
            raise InvalidActivitySubjectError("subject must not be empty")

        validated_type = _validate_type(activity_type)
        validated_status = _validate_status(status)
        validated_source = _validate_source(source)

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            contact_id=contact_id,
            activity_type=validated_type,
            subject=trimmed_subject,
            description=description.strip() if description else None,
            activity_date=activity_date,
            follow_up_date=follow_up_date,
            status=validated_status,
            source=validated_source,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    def ensure_mutable(self) -> None:
        if self.deleted_at is not None:
            raise ActivityAlreadyDeletedError("Activity is deleted")

    def update_fields(
        self,
        *,
        now: datetime,
        contact_id: Optional[UUID] = None,
        activity_type: Optional[str] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        activity_date: Optional[datetime] = None,
        follow_up_date: Optional[datetime] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        set_contact_id: bool = False,
        set_description: bool = False,
        set_follow_up_date: bool = False,
    ) -> None:
        self.ensure_mutable()

        if set_contact_id:
            self.contact_id = contact_id

        if activity_type is not None:
            self.activity_type = _validate_type(activity_type)

        if subject is not None:
            trimmed = subject.strip()
            if not trimmed:
                raise InvalidActivitySubjectError("subject must not be empty")
            self.subject = trimmed

        if set_description:
            self.description = description.strip() if description else None

        if activity_date is not None:
            self.activity_date = activity_date

        if set_follow_up_date:
            self.follow_up_date = follow_up_date

        if status is not None:
            self.status = _validate_status(status)

        if source is not None:
            self.source = _validate_source(source)

        if is_active is not None:
            self.is_active = is_active

        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        if self.deleted_at is not None:
            return
        self.deleted_at = now
        self.is_active = False
        self.updated_at = now
