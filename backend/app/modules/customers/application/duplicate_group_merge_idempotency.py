"""Return a prior successful merge result when the same merge was already executed."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.customers.application.duplicate_group_merge import MergePreviewStatistics
from app.modules.customers.application.duplicate_group_merge_execute import DuplicateGroupMergeExecuteResult
from app.modules.customers.infrastructure.persistence.mappers import model_to_entity
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.system_admin.infrastructure.persistence.models import DuplicateGroupMergeAuditLogModel


def try_get_idempotent_merge_execute_result(
    session: Session,
    *,
    organization_id: UUID,
    run_id: UUID,
    group_key: str,
    surviving_customer_id: UUID,
) -> DuplicateGroupMergeExecuteResult | None:
    audit = (
        session.query(DuplicateGroupMergeAuditLogModel)
        .filter(
            DuplicateGroupMergeAuditLogModel.organization_id == organization_id,
            DuplicateGroupMergeAuditLogModel.run_id == run_id,
            DuplicateGroupMergeAuditLogModel.group_key == group_key,
            DuplicateGroupMergeAuditLogModel.surviving_customer_id == surviving_customer_id,
        )
        .order_by(DuplicateGroupMergeAuditLogModel.executed_at.desc())
        .first()
    )
    if audit is None:
        return None

    survivor_model = session.get(CustomerModel, surviving_customer_id)
    if survivor_model is None or survivor_model.organization_id != organization_id:
        return None

    stats = audit.statistics
    statistics = MergePreviewStatistics(
        customers_before=int(stats["customers_before"]),
        customers_after=int(stats["customers_after"]),
        emails_before=int(stats["emails_before"]),
        emails_after=int(stats["emails_after"]),
        phones_before=int(stats["phones_before"]),
        phones_after=int(stats["phones_after"]),
        websites_before=int(stats["websites_before"]),
        websites_after=int(stats["websites_after"]),
    )
    return DuplicateGroupMergeExecuteResult(
        group_key=audit.group_key,
        group_by=audit.group_by,
        surviving_customer=model_to_entity(survivor_model),
        statistics=statistics,
        customers_deleted=[UUID(value) for value in audit.archived_customer_ids],
    )
