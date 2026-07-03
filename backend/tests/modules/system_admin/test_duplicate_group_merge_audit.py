"""Unit tests for duplicate group merge audit recording."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.application.duplicate_group_merge import MergePreviewStatistics
from app.modules.customers.application.duplicate_group_merge_execute import DuplicateGroupMergeExecuteResult
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.system_admin.application.duplicate_group_merge_audit import DuplicateGroupMergeAuditRecorder
from app.modules.system_admin.infrastructure.persistence.models import DuplicateGroupMergeAuditLogModel


def _customer_entity(customer_id, organization_id, *, display_name: str) -> Customer:
    now = datetime.now(tz=UTC)
    return Customer(
        id=customer_id,
        organization_id=organization_id,
        display_name=display_name,
        legal_name=None,
        trade_name=None,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD,
        status=CustomerStatus.ACTIVE,
        tax_number=None,
        tax_office=None,
        country=None,
        city=None,
        district=None,
        address=None,
        description=None,
        source=CustomerSource.MANUAL,
        created_at=now,
        updated_at=now,
        deleted_at=None,
        archived_from_status=None,
    )


def test_duplicate_group_merge_audit_recorder_persists_full_record(db_session, organization_id):
    now = datetime.now(tz=UTC)
    survivor_id = uuid4()
    archived_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()
    email_id = uuid4()

    db_session.add(
        CustomerModel(
            id=survivor_id,
            organization_id=organization_id,
            display_name="Survivor Co",
            normalized_name="survivor co",
            customer_type=CustomerType.LEAD.value,
            status=CustomerStatus.ACTIVE.value,
            source="manual",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()
    db_session.add(
        CustomerEmailModel(
            id=email_id,
            organization_id=organization_id,
            customer_id=survivor_id,
            email="merge@example.com",
            is_primary=True,
            created_at=now,
        )
    )
    db_session.flush()

    merge_result = DuplicateGroupMergeExecuteResult(
        group_key="merge@example.com",
        group_by="email",
        surviving_customer=_customer_entity(survivor_id, organization_id, display_name="Survivor Co"),
        statistics=MergePreviewStatistics(
            customers_before=2,
            customers_after=1,
            emails_before=2,
            emails_after=1,
            phones_before=0,
            phones_after=0,
            websites_before=0,
            websites_after=0,
        ),
        customers_deleted=[archived_id],
    )
    scalar_selections = {
        "company_name": survivor_id,
        "legal_name": survivor_id,
        "trade_name": survivor_id,
        "city": survivor_id,
        "country": survivor_id,
    }
    recorder = DuplicateGroupMergeAuditRecorder(
        db_session,
        SqlAlchemyCustomerCommunicationRepository(db_session),
    )
    record = recorder.record(
        organization_id=organization_id,
        executed_by_user_id=user_id,
        executed_by_user_email="auditor@example.com",
        run_id=run_id,
        merge_result=merge_result,
        scalar_selections=scalar_selections,
        selected_email_ids=[email_id],
        selected_phone_ids=[],
        selected_website_ids=[],
        executed_at=now,
    )
    db_session.flush()

    assert record.id is not None
    stored = db_session.get(DuplicateGroupMergeAuditLogModel, record.id)
    assert stored is not None
    assert stored.run_id == run_id
    assert stored.group_by == "email"
    assert stored.archived_customer_ids == [str(archived_id)]
    assert stored.scalar_field_sources["company_name"] == str(survivor_id)
    assert stored.selected_email_ids == [str(email_id)]
    assert stored.statistics["emails_after"] == 1
    assert stored.reconstruction_json["surviving_customer"]["display_name"] == "Survivor Co"
    assert stored.reconstruction_json["final_communications"]["emails"][0]["value"] == "merge@example.com"
