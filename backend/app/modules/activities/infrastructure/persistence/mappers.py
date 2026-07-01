from app.modules.activities.domain.entities import Activity
from app.modules.activities.infrastructure.persistence.models import ActivityModel


def model_to_entity(model: ActivityModel) -> Activity:
    return Activity(
        id=model.id,
        organization_id=model.organization_id,
        customer_id=model.customer_id,
        contact_id=model.contact_id,
        activity_type=model.activity_type,
        subject=model.subject,
        description=model.description,
        activity_date=model.activity_date,
        follow_up_date=model.follow_up_date,
        status=model.status,
        source=model.source,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def entity_to_model(activity: Activity) -> ActivityModel:
    return ActivityModel(
        id=activity.id,
        organization_id=activity.organization_id,
        customer_id=activity.customer_id,
        contact_id=activity.contact_id,
        activity_type=activity.activity_type,
        subject=activity.subject,
        description=activity.description,
        activity_date=activity.activity_date,
        follow_up_date=activity.follow_up_date,
        status=activity.status,
        source=activity.source,
        is_active=activity.is_active,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
        deleted_at=activity.deleted_at,
    )


def update_model_from_entity(model: ActivityModel, activity: Activity) -> None:
    model.contact_id = activity.contact_id
    model.activity_type = activity.activity_type
    model.subject = activity.subject
    model.description = activity.description
    model.activity_date = activity.activity_date
    model.follow_up_date = activity.follow_up_date
    model.status = activity.status
    model.source = activity.source
    model.is_active = activity.is_active
    model.updated_at = activity.updated_at
    model.deleted_at = activity.deleted_at
