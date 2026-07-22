from app.modules.participations.application.commands import (
    CustomerParticipationListItem,
    FairParticipantListItem,
    ParticipationResult,
)
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.ports import CustomerParticipationRow, FairParticipantRow


def participation_to_result(participation: CustomerFairParticipation) -> ParticipationResult:
    return ParticipationResult(
        id=participation.id,
        organization_id=participation.organization_id,
        customer_id=participation.customer_id,
        fair_id=participation.fair_id,
        hall=participation.hall,
        stand=participation.stand,
        notes=participation.notes,
        is_active=participation.is_active,
        created_at=participation.created_at,
        updated_at=participation.updated_at,
        deleted_at=participation.deleted_at,
    )


def customer_row_to_list_item(row: CustomerParticipationRow) -> CustomerParticipationListItem:
    p = row.participation
    return CustomerParticipationListItem(
        id=p.id,
        fair_id=p.fair_id,
        fair_name=row.fair_name,
        fair_start_date=row.fair_start_date,
        fair_end_date=row.fair_end_date,
        hall=p.hall,
        stand=p.stand,
        notes=p.notes,
    )


def fair_row_to_list_item(row: FairParticipantRow) -> FairParticipantListItem:
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
        notes=p.notes,
    )
