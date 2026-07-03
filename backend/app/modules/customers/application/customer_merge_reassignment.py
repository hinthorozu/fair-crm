"""Reassign all customer foreign-key relationships during duplicate merge."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.mappers import model_to_entity, update_model_from_entity
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.imports.infrastructure.persistence.models import ImportRowModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel


class CustomerMergeReassignmentError(ValueError):
    """Raised when loser customers still have related rows after reassignment."""


def reassign_loser_customer_relationships(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
) -> None:
    if not loser_ids:
        return

    _reassign_participations(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        loser_ids=loser_ids,
        now=now,
    )
    _reassign_customer_child_rows(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        loser_ids=loser_ids,
        now=now,
        model=ContactModel,
    )
    _reassign_customer_child_rows(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        loser_ids=loser_ids,
        now=now,
        model=ActivityModel,
    )
    _reassign_import_row_customer_references(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        loser_ids=loser_ids,
        now=now,
    )
    assert_no_loser_customer_relationships_remain(
        session,
        organization_id=organization_id,
        loser_ids=loser_ids,
    )


def mark_loser_customers_deleted(
    session: Session,
    *,
    organization_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
) -> None:
    for loser_id in loser_ids:
        loser_model = session.get(CustomerModel, loser_id)
        if loser_model is None:
            raise CustomerMergeReassignmentError(f"Customer {loser_id} not found")
        if loser_model.organization_id != organization_id:
            raise CustomerMergeReassignmentError(f"Customer {loser_id} not found in organization")
        loser_entity = model_to_entity(loser_model)
        loser_entity.mark_deleted(now=now)
        update_model_from_entity(loser_model, loser_entity)


def assert_no_loser_customer_relationships_remain(
    session: Session,
    *,
    organization_id: UUID,
    loser_ids: list[UUID],
) -> None:
    if not loser_ids:
        return

    remaining: list[str] = []
    checks: list[tuple[type, str]] = [
        (ContactModel, "customer_id"),
        (ActivityModel, "customer_id"),
        (CustomerFairParticipationModel, "customer_id"),
        (CustomerEmailModel, "customer_id"),
        (CustomerPhoneModel, "customer_id"),
        (CustomerWebsiteModel, "customer_id"),
    ]
    for model, attr in checks:
        count = (
            session.query(model)
            .filter(
                model.organization_id == organization_id,
                getattr(model, attr).in_(loser_ids),
            )
            .count()
        )
        if count:
            remaining.append(f"{model.__tablename__}={count}")

    import_count = (
        session.query(ImportRowModel)
        .filter(
            ImportRowModel.organization_id == organization_id,
            or_(
                ImportRowModel.match_customer_id.in_(loser_ids),
                ImportRowModel.created_customer_id.in_(loser_ids),
                ImportRowModel.updated_customer_id.in_(loser_ids),
            ),
        )
        .count()
    )
    if import_count:
        remaining.append(f"crm_import_rows={import_count}")

    if remaining:
        raise CustomerMergeReassignmentError(
            "Cannot delete merge losers until all related records are reassigned: "
            + ", ".join(remaining)
        )


def _reassign_participations(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
) -> None:
    survivor_fair_ids = {
        row.fair_id
        for row in session.query(CustomerFairParticipationModel)
        .filter(
            CustomerFairParticipationModel.organization_id == organization_id,
            CustomerFairParticipationModel.customer_id == survivor_id,
            CustomerFairParticipationModel.deleted_at.is_(None),
        )
        .all()
    }

    loser_participations = (
        session.query(CustomerFairParticipationModel)
        .filter(
            CustomerFairParticipationModel.organization_id == organization_id,
            CustomerFairParticipationModel.customer_id.in_(loser_ids),
            CustomerFairParticipationModel.deleted_at.is_(None),
        )
        .all()
    )

    for participation in loser_participations:
        if participation.fair_id in survivor_fair_ids:
            participation.deleted_at = now
            participation.updated_at = now
            continue
        participation.customer_id = survivor_id
        participation.updated_at = now
        survivor_fair_ids.add(participation.fair_id)

    session.flush()

    session.query(CustomerFairParticipationModel).filter(
        CustomerFairParticipationModel.organization_id == organization_id,
        CustomerFairParticipationModel.customer_id.in_(loser_ids),
        CustomerFairParticipationModel.deleted_at.isnot(None),
    ).update(
        {CustomerFairParticipationModel.customer_id: survivor_id, CustomerFairParticipationModel.updated_at: now},
        synchronize_session=False,
    )


def _reassign_customer_child_rows(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
    model: type[ContactModel] | type[ActivityModel],
) -> None:
    session.query(model).filter(
        model.organization_id == organization_id,
        model.customer_id.in_(loser_ids),
    ).update(
        {model.customer_id: survivor_id, model.updated_at: now},
        synchronize_session=False,
    )


def _reassign_import_row_customer_references(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
) -> None:
    loser_set = set(loser_ids)
    rows = (
        session.query(ImportRowModel)
        .filter(
            ImportRowModel.organization_id == organization_id,
            or_(
                ImportRowModel.match_customer_id.in_(loser_ids),
                ImportRowModel.created_customer_id.in_(loser_ids),
                ImportRowModel.updated_customer_id.in_(loser_ids),
            ),
        )
        .all()
    )
    for row in rows:
        changed = False
        if row.match_customer_id in loser_set:
            row.match_customer_id = survivor_id
            changed = True
        if row.created_customer_id in loser_set:
            row.created_customer_id = survivor_id
            changed = True
        if row.updated_customer_id in loser_set:
            row.updated_customer_id = survivor_id
            changed = True
        if changed:
            row.updated_at = now
