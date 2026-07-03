"""Persist duplicate group merge using preview output as the single source of truth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.customers.application.customer_merge_reassignment import (
    CustomerMergeReassignmentError,
    mark_loser_customers_deleted,
    reassign_loser_customer_relationships,
)
from app.modules.customers.application.duplicate_group_merge import (
    DuplicateGroupMergePreviewResult,
    MergePreviewCommunicationItem,
    MergePreviewStatistics,
)
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerStatus
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.mappers import model_to_entity, update_model_from_entity
from app.modules.customers.infrastructure.persistence.models import CustomerModel

ModelT = TypeVar("ModelT")


@dataclass(frozen=True)
class DuplicateGroupMergeExecuteResult:
    group_key: str
    group_by: str
    surviving_customer: Customer
    statistics: MergePreviewStatistics
    customers_deleted: list[UUID]


class DuplicateGroupMergeExecuteError(ValueError):
    """Raised when merge execute cannot proceed."""


def execute_duplicate_group_merge(
    session: Session,
    *,
    organization_id: UUID,
    preview: DuplicateGroupMergePreviewResult,
    member_customer_ids: list[UUID],
    now: datetime | None = None,
) -> DuplicateGroupMergeExecuteResult:
    if not preview.is_valid:
        message = (
            preview.validation_errors[0].message
            if preview.validation_errors
            else "Merge preview is not valid"
        )
        raise DuplicateGroupMergeExecuteError(message)

    timestamp = now or datetime.now(tz=UTC)
    survivor_id = preview.surviving_customer_id
    loser_ids = list(preview.customers_to_archive)

    try:
        survivor_model = session.get(CustomerModel, survivor_id)
        if survivor_model is None or survivor_model.organization_id != organization_id:
            raise DuplicateGroupMergeExecuteError("Surviving customer not found")
        if survivor_model.status == CustomerStatus.DELETED.value:
            raise DuplicateGroupMergeExecuteError("Surviving customer is deleted")

        for loser_id in loser_ids:
            loser_model = session.get(CustomerModel, loser_id)
            if loser_model is None or loser_model.organization_id != organization_id:
                raise DuplicateGroupMergeExecuteError(f"Customer {loser_id} not found in organization")
            if loser_model.status == CustomerStatus.DELETED.value:
                raise DuplicateGroupMergeExecuteError(f"Customer {loser_id} is deleted")
            if loser_id not in member_customer_ids:
                raise DuplicateGroupMergeExecuteError(f"Customer {loser_id} is not in the merge group")

        _apply_communications(
            session,
            organization_id=organization_id,
            survivor_id=survivor_id,
            member_customer_ids=member_customer_ids,
            emails=preview.emails,
            phones=preview.phones,
            websites=preview.websites,
        )
        try:
            reassign_loser_customer_relationships(
                session,
                organization_id=organization_id,
                survivor_id=survivor_id,
                loser_ids=loser_ids,
                now=timestamp,
            )
        except CustomerMergeReassignmentError as exc:
            raise DuplicateGroupMergeExecuteError(str(exc)) from exc

        update_model_from_entity(survivor_model, preview.merged_customer)
        survivor_model.updated_at = timestamp
        session.flush()

        mark_loser_customers_deleted(
            session,
            organization_id=organization_id,
            loser_ids=loser_ids,
            now=timestamp,
        )
        session.flush()
    except IntegrityError as exc:
        raise DuplicateGroupMergeExecuteError(
            "Merge failed due to overlapping fair participations. "
            "Resolve duplicate fair assignments and retry."
        ) from exc

    surviving_customer = model_to_entity(survivor_model)
    return DuplicateGroupMergeExecuteResult(
        group_key=preview.group_key,
        group_by=preview.group_by,
        surviving_customer=surviving_customer,
        statistics=preview.statistics,
        customers_deleted=loser_ids,
    )


def _apply_communications(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    member_customer_ids: list[UUID],
    emails: list[MergePreviewCommunicationItem],
    phones: list[MergePreviewCommunicationItem],
    websites: list[MergePreviewCommunicationItem],
) -> None:
    _apply_communication_channel(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        member_customer_ids=member_customer_ids,
        model=CustomerEmailModel,
        value_attr="email",
        items=emails,
    )
    _apply_communication_channel(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        member_customer_ids=member_customer_ids,
        model=CustomerPhoneModel,
        value_attr="phone",
        items=phones,
    )
    _apply_communication_channel(
        session,
        organization_id=organization_id,
        survivor_id=survivor_id,
        member_customer_ids=member_customer_ids,
        model=CustomerWebsiteModel,
        value_attr="website",
        items=websites,
    )


def _apply_communication_channel(
    session: Session,
    *,
    organization_id: UUID,
    survivor_id: UUID,
    member_customer_ids: list[UUID],
    model: type[ModelT],
    value_attr: str,
    items: list[MergePreviewCommunicationItem],
) -> None:
    winning_ids = {item.source_row_id for item in items}

    for item in items:
        row = session.get(model, item.source_row_id)
        if row is None:
            raise DuplicateGroupMergeExecuteError(f"Communication row {item.source_row_id} not found")
        if row.organization_id != organization_id:
            raise DuplicateGroupMergeExecuteError(f"Communication row {item.source_row_id} not found")
        if row.customer_id not in member_customer_ids:
            raise DuplicateGroupMergeExecuteError(
                f"Communication row {item.source_row_id} does not belong to the merge group"
            )
        setattr(row, value_attr, item.value)
        row.customer_id = survivor_id
        row.is_primary = item.is_primary

    delete_query = session.query(model).filter(
        model.organization_id == organization_id,
        model.customer_id.in_(member_customer_ids),
    )
    if winning_ids:
        delete_query = delete_query.filter(~model.id.in_(winning_ids))
    delete_query.delete(synchronize_session=False)
