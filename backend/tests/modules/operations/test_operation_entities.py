from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.operations.domain.entities import Operation, OperationRun, OperationRunItem
from app.modules.operations.domain.exceptions import (
    InvalidOperationStatusTransitionError,
    InvalidOperationTitleError,
)
from app.modules.operations.domain.value_objects import (
    OperationStatus,
    OperationType,
    RunItemStatus,
    RunStatus,
    SourceKind,
)


def test_operation_create_requires_title():
    now = datetime.now(tz=UTC)
    try:
        Operation.create(
            organization_id=uuid4(),
            operation_type=OperationType.MANUAL_TASK,
            title="  ",
            created_by=uuid4(),
            now=now,
        )
        assert False, "expected InvalidOperationTitleError"
    except InvalidOperationTitleError:
        pass


def test_operation_status_transitions():
    now = datetime.now(tz=UTC)
    operation = Operation.create(
        organization_id=uuid4(),
        operation_type=OperationType.MANUAL_TASK,
        title="Call customer",
        created_by=uuid4(),
        now=now,
        source_kind=SourceKind.CUSTOMER,
        type_config={"title": "Call customer", "status": "open"},
    )
    user_id = uuid4()
    operation.transition_status(OperationStatus.READY, now=now, updated_by=user_id)
    operation.transition_status(OperationStatus.ACTIVE, now=now, updated_by=user_id)
    try:
        operation.transition_status(OperationStatus.DRAFT, now=now, updated_by=user_id)
        assert False, "expected InvalidOperationStatusTransitionError"
    except InvalidOperationStatusTransitionError:
        pass


def test_run_progress_and_completion():
    now = datetime.now(tz=UTC)
    run = OperationRun.create(
        organization_id=uuid4(),
        operation_id=uuid4(),
        now=now,
        total_items=10,
    )
    run.transition_status(RunStatus.RUNNING, now=now)
    assert run.started_at is not None
    run.update_progress(now=now, processed_items=4, succeeded_items=3, failed_items=1)
    assert run.progress == 0.4
    run.transition_status(RunStatus.COMPLETED, now=now)
    assert run.finished_at is not None
    assert run.status == RunStatus.COMPLETED


def test_run_item_retry_lifecycle():
    now = datetime.now(tz=UTC)
    item = OperationRunItem.create(
        organization_id=uuid4(),
        run_id=uuid4(),
        operation_id=uuid4(),
        now=now,
        item_key="customer:1",
        target_type="customer",
        target_id=uuid4(),
    )
    item.mark_processing(now=now)
    item.mark_failed(now=now, error_code="timeout", error_message="timed out")
    assert item.status == RunItemStatus.FAILED
    later = now + timedelta(seconds=1)
    item.prepare_retry(now=later)
    assert item.status == RunItemStatus.PENDING
    assert item.attempt == 2
    assert item.error_code is None
