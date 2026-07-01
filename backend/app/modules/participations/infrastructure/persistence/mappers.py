from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel


def model_to_entity(model: CustomerFairParticipationModel) -> CustomerFairParticipation:
    return CustomerFairParticipation(
        id=model.id,
        organization_id=model.organization_id,
        customer_id=model.customer_id,
        fair_id=model.fair_id,
        hall=model.hall,
        stand=model.stand,
        participation_status=model.participation_status,
        notes=model.notes,
        primary_contact_id=model.primary_contact_id,
        visited_at=model.visited_at,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def entity_to_model(entity: CustomerFairParticipation) -> CustomerFairParticipationModel:
    return CustomerFairParticipationModel(
        id=entity.id,
        organization_id=entity.organization_id,
        customer_id=entity.customer_id,
        fair_id=entity.fair_id,
        hall=entity.hall,
        stand=entity.stand,
        participation_status=entity.participation_status,
        notes=entity.notes,
        primary_contact_id=entity.primary_contact_id,
        visited_at=entity.visited_at,
        is_active=entity.is_active,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        deleted_at=entity.deleted_at,
    )


def update_model_from_entity(
    model: CustomerFairParticipationModel, entity: CustomerFairParticipation
) -> None:
    model.hall = entity.hall
    model.stand = entity.stand
    model.participation_status = entity.participation_status
    model.notes = entity.notes
    model.primary_contact_id = entity.primary_contact_id
    model.visited_at = entity.visited_at
    model.is_active = entity.is_active
    model.updated_at = entity.updated_at
    model.deleted_at = entity.deleted_at
