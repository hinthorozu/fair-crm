"""Batch enrichment for activity list/detail responses (avoids N+1)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.activities.application.commands import ActivityResult
from app.modules.activities.application.mappers import activity_to_result
from app.modules.activities.domain.entities import Activity
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.todos.infrastructure.persistence.models import (
    TodoModel,
    TodoOutcomeDefinitionModel,
    TodoWorklistStateModel,
)


def _parse_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _metadata_fields(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {
            "related_todo_id": None,
            "related_outcome_id": None,
            "is_worklist": False,
            "display_metadata": {},
        }

    related_todo_id = _parse_uuid(metadata.get("todo_id"))
    related_outcome_id = _parse_uuid(metadata.get("outcome_id"))
    is_worklist = bool(metadata.get("worklist"))

    # User-facing subset only — never dump raw technical keys.
    display: dict[str, Any] = {}
    source_label = metadata.get("source")
    if isinstance(source_label, str) and source_label and source_label != "fair_bulk_email":
        display["source_detail"] = source_label
    elif source_label == "fair_bulk_email":
        display["source_detail"] = "Fuar toplu e-posta"
        if metadata.get("delivery_status"):
            display["delivery_status"] = metadata["delivery_status"]
        if metadata.get("recipient_email"):
            display["recipient_email"] = metadata["recipient_email"]

    return {
        "related_todo_id": related_todo_id,
        "related_outcome_id": related_outcome_id,
        "is_worklist": is_worklist,
        "display_metadata": display,
    }


def enrich_activities(
    session: Session,
    customer_repository: CustomerRepository,
    contact_repository: ContactRepository,
    organization_id: UUID,
    activities: list[Activity],
) -> list[ActivityResult]:
    if not activities:
        return []

    activity_ids = [a.id for a in activities]
    customer_ids = {a.customer_id for a in activities if a.customer_id is not None}
    contact_ids = {a.contact_id for a in activities if a.contact_id}

    customer_names: dict[UUID, str] = {}
    for customer_id in customer_ids:
        customer = customer_repository.get_by_id(organization_id, customer_id)
        if customer is not None:
            customer_names[customer_id] = customer.display_name

    contact_names: dict[UUID, str] = {}
    for contact_id in contact_ids:
        contact = contact_repository.get_by_id(organization_id, contact_id)
        if contact is not None:
            contact_names[contact_id] = contact.full_name

    meta_by_activity: dict[UUID, dict[str, Any]] = {}
    todo_ids: set[UUID] = set()
    outcome_ids: set[UUID] = set()
    for activity in activities:
        parsed = _metadata_fields(activity.metadata_json)
        related_todo_id = activity.todo_id or parsed["related_todo_id"]
        parsed = {**parsed, "related_todo_id": related_todo_id}
        meta_by_activity[activity.id] = parsed
        if related_todo_id:
            todo_ids.add(related_todo_id)
        if parsed["related_outcome_id"]:
            outcome_ids.add(parsed["related_outcome_id"])

    todo_titles: dict[UUID, str] = {}
    if todo_ids:
        rows = (
            session.query(TodoModel.id, TodoModel.title)
            .filter(
                TodoModel.organization_id == organization_id,
                TodoModel.id.in_(todo_ids),
            )
            .all()
        )
        todo_titles = {row.id: row.title for row in rows}

    outcome_names: dict[UUID, str] = {}
    if outcome_ids:
        rows = (
            session.query(TodoOutcomeDefinitionModel.id, TodoOutcomeDefinitionModel.name)
            .filter(
                TodoOutcomeDefinitionModel.organization_id == organization_id,
                TodoOutcomeDefinitionModel.id.in_(outcome_ids),
            )
            .all()
        )
        outcome_names = {row.id: row.name for row in rows}

    worklist_by_activity: dict[UUID, TodoWorklistStateModel] = {}
    if activity_ids:
        states = (
            session.query(TodoWorklistStateModel)
            .filter(
                TodoWorklistStateModel.organization_id == organization_id,
                TodoWorklistStateModel.last_activity_id.in_(activity_ids),
            )
            .all()
        )
        for state in states:
            if state.last_activity_id is not None:
                worklist_by_activity[state.last_activity_id] = state

    results: list[ActivityResult] = []
    for activity in activities:
        meta = meta_by_activity[activity.id]
        state = worklist_by_activity.get(activity.id)
        related_todo_id = meta["related_todo_id"]
        related_outcome_id = meta["related_outcome_id"]
        results.append(
            activity_to_result(
                activity,
                contact_full_name=contact_names.get(activity.contact_id) if activity.contact_id else None,
                customer_name=(
                    customer_names.get(activity.customer_id) if activity.customer_id else None
                ),
                related_todo_id=related_todo_id,
                related_todo_title=todo_titles.get(related_todo_id) if related_todo_id else None,
                related_outcome_id=related_outcome_id,
                related_outcome_name=outcome_names.get(related_outcome_id) if related_outcome_id else None,
                action_required=state.action_required if state is not None else None,
                data_problem=state.data_problem if state is not None else None,
                display_metadata=meta["display_metadata"] or None,
            )
        )
    return results
