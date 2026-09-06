from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleSnapshot,
    OrganizationLifecycleUnavailableError,
)
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.imports.domain.value_objects import ImportJobStatus, ImportJobType
from app.modules.system_admin.domain.data_operation_entities import DataOperationRun
from app.modules.system_admin.domain.data_operation_value_objects import DataOperationRunStatus
from app.shared.running_work_lifecycle import (
    RunningWorkLifecycleCancelledError,
    RunningWorkLifecycleCheckpoint,
)


class _Guard:
    def __init__(self, result):
        self._result = result

    def get_snapshot(self, organization_id):
        if isinstance(self._result, Exception):
            raise self._result
        assert self._result.organization_id == organization_id
        return self._result


def test_running_checkpoint_allows_active_organization():
    organization_id = uuid4()
    snapshot = OrganizationLifecycleSnapshot(
        organization_id=organization_id,
        status="active",
        work_allowed=True,
    )

    result = RunningWorkLifecycleCheckpoint(
        organization_id,
        guard=_Guard(snapshot),  # type: ignore[arg-type]
    ).check()

    assert result == snapshot


def test_running_checkpoint_cancels_explicit_suspension():
    organization_id = uuid4()
    snapshot = OrganizationLifecycleSnapshot(
        organization_id=organization_id,
        status="suspended",
        work_allowed=False,
    )

    with pytest.raises(RunningWorkLifecycleCancelledError) as exc_info:
        RunningWorkLifecycleCheckpoint(
            organization_id,
            guard=_Guard(snapshot),  # type: ignore[arg-type]
        ).check()

    assert exc_info.value.organization_id == organization_id
    assert exc_info.value.status == "suspended"


def test_running_checkpoint_does_not_mislabel_authority_outage_as_cancellation():
    organization_id = uuid4()
    unavailable = OrganizationLifecycleUnavailableError("authority unavailable")

    with pytest.raises(OrganizationLifecycleUnavailableError):
        RunningWorkLifecycleCheckpoint(
            organization_id,
            guard=_Guard(unavailable),  # type: ignore[arg-type]
        ).check()


def test_running_import_job_can_terminalize_as_cancelled():
    now = datetime.now(tz=UTC)
    job = ImportJob(
        id=uuid4(),
        organization_id=uuid4(),
        batch_id=uuid4(),
        job_type=ImportJobType.APPLY,
        status=ImportJobStatus.RUNNING,
        progress_processed=3,
        progress_total=10,
        result_json=None,
        error_message=None,
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=None,
    )

    job.mark_cancelled(error_message="suspended", now=now)

    assert job.status == ImportJobStatus.CANCELLED
    assert job.error_message == "suspended"
    assert job.completed_at == now


def test_running_data_operation_can_terminalize_as_cancelled():
    now = datetime.now(tz=UTC)
    run = DataOperationRun.create(
        organization_id=uuid4(),
        operation_key="analyze_customers_without_fair",
        started_by=uuid4(),
        started_by_email=None,
        now=now,
    )
    run.mark_running(now=now)

    run.mark_cancelled(error_message="suspended", now=now)

    assert run.status == DataOperationRunStatus.CANCELLED
    assert run.error_message == "suspended"
    assert run.completed_at == now
