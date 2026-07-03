"""Persist audit records for successful duplicate group merge executions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.customers.application.duplicate_group_merge import MergePreviewStatistics
from app.modules.customers.application.duplicate_group_merge_execute import DuplicateGroupMergeExecuteResult
from app.modules.customers.domain.communication_entities import CustomerCommunications
from app.modules.customers.domain.entities import Customer
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.system_admin.infrastructure.persistence.models import DuplicateGroupMergeAuditLogModel


@dataclass(frozen=True)
class DuplicateGroupMergeAuditRecord:
    id: UUID
    organization_id: UUID
    executed_at: datetime
    executed_by_user_id: UUID
    executed_by_user_email: str | None
    run_id: UUID
    group_key: str
    group_by: str
    surviving_customer_id: UUID
    archived_customer_ids: list[UUID]
    scalar_field_sources: dict[str, UUID]
    selected_email_ids: list[UUID]
    selected_phone_ids: list[UUID]
    selected_website_ids: list[UUID]
    statistics: MergePreviewStatistics
    reconstruction_json: dict[str, Any]


def _uuid_list_to_json(values: list[UUID]) -> list[str]:
    return [str(value) for value in values]


def _uuid_map_to_json(values: dict[str, UUID]) -> dict[str, str]:
    return {key: str(value) for key, value in values.items()}


def _statistics_to_json(statistics: MergePreviewStatistics) -> dict[str, int]:
    return {
        "customers_before": statistics.customers_before,
        "customers_after": statistics.customers_after,
        "emails_before": statistics.emails_before,
        "emails_after": statistics.emails_after,
        "phones_before": statistics.phones_before,
        "phones_after": statistics.phones_after,
        "websites_before": statistics.websites_before,
        "websites_after": statistics.websites_after,
    }


def _customer_snapshot(customer: Customer) -> dict[str, Any]:
    return {
        "id": str(customer.id),
        "display_name": customer.display_name,
        "legal_name": customer.legal_name,
        "trade_name": customer.trade_name,
        "normalized_name": customer.normalized_name,
        "customer_type": customer.customer_type.value,
        "status": customer.status.value,
        "tax_number": customer.tax_number,
        "tax_office": customer.tax_office,
        "country": customer.country,
        "city": customer.city,
        "district": customer.district,
        "address": customer.address,
        "description": customer.description,
        "source": customer.source.value,
        "updated_at": customer.updated_at.isoformat(),
    }


def _communications_snapshot(communications: CustomerCommunications) -> dict[str, list[dict[str, Any]]]:
    return {
        "emails": [
            {
                "id": str(item.id),
                "value": item.email,
                "is_primary": item.is_primary,
                "created_at": item.created_at.isoformat(),
            }
            for item in communications.emails
        ],
        "phones": [
            {
                "id": str(item.id),
                "value": item.phone,
                "is_primary": item.is_primary,
                "created_at": item.created_at.isoformat(),
            }
            for item in communications.phones
        ],
        "websites": [
            {
                "id": str(item.id),
                "value": item.website,
                "is_primary": item.is_primary,
                "created_at": item.created_at.isoformat(),
            }
            for item in communications.websites
        ],
    }


def build_duplicate_group_merge_reconstruction(
    *,
    merge_result: DuplicateGroupMergeExecuteResult,
    final_communications: CustomerCommunications,
) -> dict[str, Any]:
    return {
        "surviving_customer": _customer_snapshot(merge_result.surviving_customer),
        "final_communications": _communications_snapshot(final_communications),
        "deleted_customer_ids": [str(customer_id) for customer_id in merge_result.customers_deleted],
    }


class DuplicateGroupMergeAuditRecorder:
    """Writes one audit row per successful merge execute (after merge transaction commit)."""

    def __init__(
        self,
        session: Session,
        communication_repository: SqlAlchemyCustomerCommunicationRepository,
    ) -> None:
        self._session = session
        self._communication_repository = communication_repository

    def record(
        self,
        *,
        organization_id: UUID,
        executed_by_user_id: UUID,
        executed_by_user_email: str | None,
        run_id: UUID,
        merge_result: DuplicateGroupMergeExecuteResult,
        scalar_selections: dict[str, UUID],
        selected_email_ids: list[UUID],
        selected_phone_ids: list[UUID],
        selected_website_ids: list[UUID],
        executed_at: datetime | None = None,
    ) -> DuplicateGroupMergeAuditRecord:
        timestamp = executed_at or datetime.now(tz=UTC)
        final_communications = self._communication_repository.load_for_customer(
            merge_result.surviving_customer.id
        )
        reconstruction_json = build_duplicate_group_merge_reconstruction(
            merge_result=merge_result,
            final_communications=final_communications,
        )
        audit_id = uuid4()
        model = DuplicateGroupMergeAuditLogModel(
            id=audit_id,
            organization_id=organization_id,
            executed_at=timestamp,
            executed_by_user_id=executed_by_user_id,
            executed_by_user_email=executed_by_user_email,
            run_id=run_id,
            group_key=merge_result.group_key,
            group_by=merge_result.group_by,
            surviving_customer_id=merge_result.surviving_customer.id,
            archived_customer_ids=_uuid_list_to_json(merge_result.customers_deleted),
            scalar_field_sources=_uuid_map_to_json(scalar_selections),
            selected_email_ids=_uuid_list_to_json(selected_email_ids),
            selected_phone_ids=_uuid_list_to_json(selected_phone_ids),
            selected_website_ids=_uuid_list_to_json(selected_website_ids),
            statistics=_statistics_to_json(merge_result.statistics),
            reconstruction_json=reconstruction_json,
            created_at=timestamp,
        )
        self._session.add(model)
        self._session.flush()
        return DuplicateGroupMergeAuditRecord(
            id=audit_id,
            organization_id=organization_id,
            executed_at=timestamp,
            executed_by_user_id=executed_by_user_id,
            executed_by_user_email=executed_by_user_email,
            run_id=run_id,
            group_key=merge_result.group_key,
            group_by=merge_result.group_by,
            surviving_customer_id=merge_result.surviving_customer.id,
            archived_customer_ids=list(merge_result.customers_deleted),
            scalar_field_sources=dict(scalar_selections),
            selected_email_ids=list(selected_email_ids),
            selected_phone_ids=list(selected_phone_ids),
            selected_website_ids=list(selected_website_ids),
            statistics=merge_result.statistics,
            reconstruction_json=reconstruction_json,
        )
