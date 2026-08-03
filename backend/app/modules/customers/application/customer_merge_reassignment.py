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
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailOutboxModel
from app.modules.imports.infrastructure.persistence.models import ImportRowModel
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel
from app.modules.todos.infrastructure.persistence.models import TodoModel, TodoWorklistStateModel


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
    _reassign_todos(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        loser_ids=loser_ids,
        now=now,
    )
    _reassign_todo_worklist_states(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        loser_ids=loser_ids,
        now=now,
    )
    _reassign_enrichment_states(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        loser_ids=loser_ids,
        now=now,
    )
    _reassign_import_row_customer_references(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        loser_ids=loser_ids,
        now=now,
    )
    _reassign_soft_customer_references(
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


def hard_delete_loser_customers(
    session: Session,
    *,
    organization_id: UUID,
    loser_ids: list[UUID],
) -> None:
    """Physically delete loser customer rows. Soft-delete is intentionally not used."""
    if not loser_ids:
        return

    assert_no_loser_customer_relationships_remain(
        session,
        organization_id=organization_id,
        loser_ids=loser_ids,
    )

    for loser_id in loser_ids:
        loser_model = session.get(CustomerModel, loser_id)
        if loser_model is None:
            raise CustomerMergeReassignmentError(f"Customer {loser_id} not found")
        if loser_model.organization_id != organization_id:
            raise CustomerMergeReassignmentError(f"Customer {loser_id} not found in organization")
        session.delete(loser_model)

    session.flush()


# Backwards-compatible alias for older imports/tests.
mark_loser_customers_deleted = hard_delete_loser_customers


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
        (TodoModel, "customer_id"),
        (TodoWorklistStateModel, "customer_id"),
        (CustomerEnrichmentStateModel, "customer_id"),
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

    outbox_count = (
        session.query(FairEmailOutboxModel)
        .filter(
            FairEmailOutboxModel.organization_id == organization_id,
            FairEmailOutboxModel.customer_id.in_(loser_ids),
        )
        .count()
    )
    if outbox_count:
        remaining.append(f"mail_send_operations={outbox_count}")

    mail_ops_count = (
        session.query(MailSendOperationModel)
        .filter(
            MailSendOperationModel.organization_id == organization_id,
            MailSendOperationModel.customer_id.in_(loser_ids),
        )
        .count()
    )
    if mail_ops_count:
        remaining.append(f"mail_send_operations={mail_ops_count}")

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
            # Keep survivor's active participation; soft-delete loser's duplicate then move
            # history under survivor (existing merge semantics).
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
        {
            CustomerFairParticipationModel.customer_id: survivor_id,
            CustomerFairParticipationModel.updated_at: now,
        },
        synchronize_session=False,
    )
    session.flush()


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
    session.flush()


def _reassign_todos(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
) -> None:
    session.query(TodoModel).filter(
        TodoModel.organization_id == organization_id,
        TodoModel.customer_id.in_(loser_ids),
    ).update(
        {TodoModel.customer_id: survivor_id, TodoModel.updated_at: now},
        synchronize_session=False,
    )
    session.flush()


def _reassign_todo_worklist_states(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
) -> None:
    survivor_todo_ids = {
        row.todo_id
        for row in session.query(TodoWorklistStateModel)
        .filter(
            TodoWorklistStateModel.organization_id == organization_id,
            TodoWorklistStateModel.customer_id == survivor_id,
        )
        .all()
    }

    loser_rows = (
        session.query(TodoWorklistStateModel)
        .filter(
            TodoWorklistStateModel.organization_id == organization_id,
            TodoWorklistStateModel.customer_id.in_(loser_ids),
        )
        .all()
    )
    for row in loser_rows:
        if row.todo_id in survivor_todo_ids:
            session.delete(row)
            continue
        row.customer_id = survivor_id
        row.updated_at = now
        survivor_todo_ids.add(row.todo_id)
    session.flush()


def _reassign_enrichment_states(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
) -> None:
    survivor_exists = (
        session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id == survivor_id,
        )
        .first()
        is not None
    )
    loser_rows = (
        session.query(CustomerEnrichmentStateModel)
        .filter(
            CustomerEnrichmentStateModel.organization_id == organization_id,
            CustomerEnrichmentStateModel.customer_id.in_(loser_ids),
        )
        .order_by(CustomerEnrichmentStateModel.updated_at.desc())
        .all()
    )
    if survivor_exists or not loser_rows:
        for row in loser_rows:
            session.delete(row)
    else:
        keep = loser_rows[0]
        keep.customer_id = survivor_id
        keep.updated_at = now
        for row in loser_rows[1:]:
            session.delete(row)
    session.flush()


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
    session.flush()


def _reassign_soft_customer_references(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    loser_ids: list[UUID],
    now: datetime,
) -> None:
    """Reassign soft (non-FK) customer_id columns so losers can be hard-deleted cleanly."""
    session.query(FairEmailOutboxModel).filter(
        FairEmailOutboxModel.organization_id == organization_id,
        FairEmailOutboxModel.customer_id.in_(loser_ids),
    ).update(
        {FairEmailOutboxModel.customer_id: survivor_id, FairEmailOutboxModel.updated_at: now},
        synchronize_session=False,
    )
    session.query(MailSendOperationModel).filter(
        MailSendOperationModel.organization_id == organization_id,
        MailSendOperationModel.customer_id.in_(loser_ids),
    ).update(
        {MailSendOperationModel.customer_id: survivor_id, MailSendOperationModel.updated_at: now},
        synchronize_session=False,
    )
    session.flush()
