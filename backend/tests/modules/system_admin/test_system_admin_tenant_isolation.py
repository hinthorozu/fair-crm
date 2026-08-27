"""Tenant-isolation evidence for organization-owned system-admin run records."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.system_admin.infrastructure.persistence.models import (
    SystemDataOperationRunModel,
)
from app.modules.system_admin.infrastructure.repositories.data_operation_run_repository import (
    SqlAlchemyDataOperationRunRepository,
)


def test_data_operation_run_direct_foreign_id_is_hidden(
    db_session,
    organization_id,
    other_organization_id,
):
    now = datetime.now(tz=UTC)
    run_id = uuid4()
    db_session.add(
        SystemDataOperationRunModel(
            id=run_id,
            organization_id=organization_id,
            operation_key="duplicate_customer_analysis",
            status="completed",
            started_by=uuid4(),
            started_by_email="owner@example.com",
            started_at=now,
            completed_at=now,
            duration_seconds=0,
            result="success",
            error_message=None,
            stdout_text=None,
            output_files_json=None,
            summary_json={},
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()

    repository = SqlAlchemyDataOperationRunRepository(db_session)
    assert repository.get_by_id(organization_id, run_id) is not None
    assert repository.get_by_id(other_organization_id, run_id) is None
