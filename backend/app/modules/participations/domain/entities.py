"""Customer–Fair participation (exhibitor) join entity.

Hall, stand, and fair-specific notes live here — not on Customer or Fair.
A participation record means the customer is a participant of that fair.
Workflow status / visit / primary contact are legacy DB fields only.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.participations.domain.exceptions import InvalidParticipationStatusError
from app.modules.participations.domain.value_objects import ParticipationStatus


def _validate_status(value: str) -> str:
    try:
        return ParticipationStatus(value)
    except ValueError as exc:
        raise InvalidParticipationStatusError(f"Invalid participation status: {value}") from exc


@dataclass
class CustomerFairParticipation:
    id: UUID
    organization_id: UUID
    customer_id: UUID
    fair_id: UUID
    hall: Optional[str]
    stand: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    # Legacy columns retained for safe DB round-trip; not part of active business model.
    participation_status: str = ParticipationStatus.EXHIBITOR
    primary_contact_id: Optional[UUID] = None
    visited_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        customer_id: UUID,
        fair_id: UUID,
        hall: Optional[str] = None,
        stand: Optional[str] = None,
        notes: Optional[str] = None,
        participation_status: str = ParticipationStatus.EXHIBITOR,
        is_active: bool = True,
        now: datetime,
    ) -> "CustomerFairParticipation":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_id,
            fair_id=fair_id,
            hall=hall.strip() if hall else None,
            stand=stand.strip() if stand else None,
            notes=notes.strip() if notes else None,
            participation_status=_validate_status(participation_status),
            primary_contact_id=None,
            visited_at=None,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    def ensure_mutable(self) -> None:
        if self.deleted_at is not None:
            from app.modules.participations.domain.exceptions import ParticipationAlreadyDeletedError

            raise ParticipationAlreadyDeletedError("Participation is deleted")

    def update_fields(
        self,
        *,
        now: datetime,
        hall: Optional[str] = None,
        stand: Optional[str] = None,
        notes: Optional[str] = None,
        set_hall: bool = False,
        set_stand: bool = False,
        set_notes: bool = False,
    ) -> None:
        self.ensure_mutable()

        if set_hall:
            self.hall = hall.strip() if hall else None
        if set_stand:
            self.stand = stand.strip() if stand else None
        if set_notes:
            self.notes = notes.strip() if notes else None

        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        if self.deleted_at is not None:
            return
        self.deleted_at = now
        self.is_active = False
        self.updated_at = now
