"""Tests for the duplicate-start guard in StartOperationUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.operations.application.commands import StartOperationCommand
from app.modules.operations.application.start_operation import StartOperationUseCase
from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.exceptions import OperationAlreadyRunningError
from app.modules.operations.domain.value_objects import (
    HandlerCapabilities,
    OperationStatus,
    OperationType,
    RunStatus,
    SourceKind,
)


def _make_operation(*, status: OperationStatus = OperationStatus.ACTIVE) -> Operation:
    now = datetime.now(tz=UTC)
    op = Operation.create(
        organization_id=uuid4(),
        operation_type=OperationType.ENRICHMENT,
        title="Test Enrichment",
        created_by=uuid4(),
        now=now,
        source_kind=SourceKind.CUSTOMER,
        source_config={},
        type_config={"adapter_key": "customer_contact_enrichment", "requested_fields": []},
        status=status,
    )
    return op


def _make_run(*, status: RunStatus) -> OperationRun:
    now = datetime.now(tz=UTC)
    return OperationRun.create(
        organization_id=uuid4(),
        operation_id=uuid4(),
        now=now,
        triggered_by=uuid4(),
        status=status,
    )


def _make_use_case(operation: Operation, latest_run: OperationRun | None):
    """Build StartOperationUseCase with minimal mocks."""
    op_repo = MagicMock()
    op_repo.get_by_id.return_value = operation

    run_repo = MagicMock()
    # _load_latest_run resolves via get_by_id
    run_repo.get_by_id.return_value = latest_run

    # Handler that reports validation OK and leaves the run QUEUED (background worker picks it up)
    handler = MagicMock()
    handler.validate_start.return_value = SimpleNamespace(ok=True, errors=[])
    handler.on_start.return_value = SimpleNamespace(
        run_status=RunStatus.QUEUED,
        total_items=0,
        result_payload=None,
        message=None,
        related_todo_id=None,
    )
    handler.capabilities = HandlerCapabilities()

    registry = MagicMock()
    registry.get.return_value = handler

    auth = MagicMock()
    auth.check_permission.return_value = True

    audit = MagicMock()

    # Wire latest_run_id so _load_latest_run is called
    if latest_run is not None:
        operation.latest_run_id = latest_run.id

    return StartOperationUseCase(
        operation_repository=op_repo,
        run_repository=run_repo,
        handler_registry=registry,
        authorization=auth,
        audit=audit,
    )


def _command(operation_id) -> StartOperationCommand:
    return StartOperationCommand(
        organization_id=uuid4(),
        user_id=uuid4(),
        access_token="tok",
        operation_id=operation_id,
        user_email="test@example.com",
    )


@pytest.mark.parametrize("run_status", [RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.PAUSED])
def test_start_raises_when_active_run_exists(run_status: RunStatus):
    """Guard rejects duplicate start for any active run status."""
    op = _make_operation()
    run = _make_run(status=run_status)
    use_case = _make_use_case(op, run)
    with pytest.raises(OperationAlreadyRunningError):
        use_case.execute(_command(op.id))


def test_start_proceeds_when_no_latest_run():
    """No run yet → start is allowed."""
    op = _make_operation(status=OperationStatus.READY)
    op.latest_run_id = None
    use_case = _make_use_case(op, None)
    # Should not raise — run_repo.add returns a valid-looking run
    run = _make_run(status=RunStatus.QUEUED)
    run.id = uuid4()
    use_case._run_repository.add.return_value = run
    use_case._run_repository.update.return_value = run
    use_case._operation_repository.update.return_value = op
    result = use_case.execute(_command(op.id))
    assert result is not None


@pytest.mark.parametrize("run_status", [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED])
def test_start_proceeds_when_previous_run_is_terminal(run_status: RunStatus):
    """Completed / failed / cancelled run → new start is allowed."""
    op = _make_operation()
    run = _make_run(status=run_status)
    use_case = _make_use_case(op, run)
    fresh_run = _make_run(status=RunStatus.QUEUED)
    fresh_run.id = uuid4()
    use_case._run_repository.add.return_value = fresh_run
    use_case._run_repository.update.return_value = fresh_run
    use_case._operation_repository.update.return_value = op
    result = use_case.execute(_command(op.id))
    assert result is not None
