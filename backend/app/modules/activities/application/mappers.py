from typing import Any, Optional
from uuid import UUID

from app.modules.activities.application.commands import ActivityResult
from app.modules.activities.domain.entities import Activity


def activity_to_result(
    activity: Activity,
    *,
    contact_full_name: str | None = None,
    customer_name: str | None = None,
    related_todo_id: UUID | None = None,
    related_todo_title: str | None = None,
    related_outcome_id: UUID | None = None,
    related_outcome_name: str | None = None,
    action_required: bool | None = None,
    data_problem: bool | None = None,
    display_metadata: Optional[dict[str, Any]] = None,
) -> ActivityResult:
    return ActivityResult(
        id=activity.id,
        organization_id=activity.organization_id,
        customer_id=activity.customer_id,
        contact_id=activity.contact_id,
        contact_full_name=contact_full_name,
        type=activity.activity_type,
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
        todo_id=activity.todo_id,
        fair_id=activity.fair_id,
        customer_name=customer_name,
        related_todo_id=related_todo_id,
        related_todo_title=related_todo_title,
        related_outcome_id=related_outcome_id,
        related_outcome_name=related_outcome_name,
        action_required=action_required,
        data_problem=data_problem,
        display_metadata=display_metadata,
    )


def resolve_contact_full_name(
    contact_repository,
    organization_id: UUID,
    contact_id: UUID | None,
) -> str | None:
    if contact_id is None:
        return None
    contact = contact_repository.get_by_id(organization_id, contact_id)
    if contact is None:
        return None
    return contact.full_name
