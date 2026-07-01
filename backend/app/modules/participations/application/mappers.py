from uuid import UUID

from app.modules.participations.application.commands import (
    CustomerParticipationListItem,
    FairParticipantListItem,
    ParticipationResult,
)
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.ports import CustomerParticipationRow, FairParticipantRow
from app.modules.participations.domain.value_objects import ParticipationStatus


def participation_to_result(
    participation: CustomerFairParticipation,
    *,
    primary_contact_name: str | None = None,
) -> ParticipationResult:
    return ParticipationResult(
        id=participation.id,
        organization_id=participation.organization_id,
        customer_id=participation.customer_id,
        fair_id=participation.fair_id,
        hall=participation.hall,
        stand=participation.stand,
        participation_status=ParticipationStatus(participation.participation_status),
        notes=participation.notes,
        primary_contact_id=participation.primary_contact_id,
        primary_contact_name=primary_contact_name,
        visited_at=participation.visited_at,
        is_active=participation.is_active,
        created_at=participation.created_at,
        updated_at=participation.updated_at,
        deleted_at=participation.deleted_at,
    )


def customer_row_to_list_item(
    row: CustomerParticipationRow,
    *,
    primary_contact_name: str | None,
) -> CustomerParticipationListItem:
    p = row.participation
    return CustomerParticipationListItem(
        id=p.id,
        fair_id=p.fair_id,
        fair_name=row.fair_name,
        fair_start_date=row.fair_start_date,
        fair_end_date=row.fair_end_date,
        hall=p.hall,
        stand=p.stand,
        participation_status=ParticipationStatus(p.participation_status),
        primary_contact_name=primary_contact_name,
        visited_at=p.visited_at,
        notes=p.notes,
    )


def fair_row_to_list_item(
    row: FairParticipantRow,
    *,
    primary_contact_name: str | None,
) -> FairParticipantListItem:
    p = row.participation
    return FairParticipantListItem(
        id=p.id,
        customer_id=p.customer_id,
        company_name=row.company_name,
        email=row.email,
        phone=row.phone,
        country=row.country,
        city=row.city,
        hall=p.hall,
        stand=p.stand,
        participation_status=ParticipationStatus(p.participation_status),
        primary_contact_name=primary_contact_name,
        visited_at=p.visited_at,
        notes=p.notes,
    )


def resolve_primary_contact_name(repository, organization_id: UUID, contact_id: UUID | None) -> str | None:
    return repository.get_contact_full_name(organization_id, contact_id)
