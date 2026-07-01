from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel


def model_to_entity(model: FairModel) -> Fair:
    return Fair(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        organizer=model.organizer,
        venue=model.venue,
        city=model.city,
        country=model.country,
        start_date=model.start_date,
        end_date=model.end_date,
        website=model.website,
        status=FairStatus(model.status),
        description=model.description,
        normalized_name=model.normalized_name,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        archived_from_status=(
            FairStatus(model.archived_from_status) if model.archived_from_status else None
        ),
    )


def entity_to_model(fair: Fair) -> FairModel:
    return FairModel(
        id=fair.id,
        organization_id=fair.organization_id,
        name=fair.name,
        organizer=fair.organizer,
        venue=fair.venue,
        city=fair.city,
        country=fair.country,
        start_date=fair.start_date,
        end_date=fair.end_date,
        website=fair.website,
        status=fair.status.value,
        description=fair.description,
        normalized_name=fair.normalized_name,
        created_at=fair.created_at,
        updated_at=fair.updated_at,
        deleted_at=fair.deleted_at,
        archived_from_status=(
            fair.archived_from_status.value if fair.archived_from_status else None
        ),
    )


def update_model_from_entity(model: FairModel, fair: Fair) -> None:
    model.name = fair.name
    model.organizer = fair.organizer
    model.venue = fair.venue
    model.city = fair.city
    model.country = fair.country
    model.start_date = fair.start_date
    model.end_date = fair.end_date
    model.website = fair.website
    model.status = fair.status.value
    model.description = fair.description
    model.normalized_name = fair.normalized_name
    model.updated_at = fair.updated_at
    model.deleted_at = fair.deleted_at
    model.archived_from_status = (
        fair.archived_from_status.value if fair.archived_from_status else None
    )
