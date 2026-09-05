from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.modules.system_admin.application import data_operation_job_runner as runner_module
from app.modules.system_admin.application.data_operation_job_runner import (
    DataOperationJobCommand,
    DataOperationJobRunner,
)
from app.modules.system_admin.domain.data_operation_entities import DataOperationRun
from app.modules.system_admin.domain.data_operation_value_objects import DataOperationRunStatus
from app.shared.running_work_lifecycle import RunningWorkLifecycleCancelledError


class _Session:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


class _Repo:
    def __init__(self, run: DataOperationRun) -> None:
        self.run = run

    def get_by_id(self, organization_id, run_id):
        if self.run.organization_id == organization_id and self.run.id == run_id:
            return self.run
        return None

    def update(self, run):
        self.run = run
        return run


def test_running_dataset_operation_suspension_rolls_back_and_cancels(monkeypatch):
    organization_id = uuid4()
    run = DataOperationRun.create(
        organization_id=organization_id,
        operation_key="analyze_customers_without_fair",
        started_by=uuid4(),
        started_by_email=None,
        now=datetime.now(tz=UTC),
    )
    session = _Session()
    repo = _Repo(run)

    monkeypatch.setattr(runner_module, "SqlAlchemyDataOperationRunRepository", lambda _db: repo)
    monkeypatch.setattr(
        runner_module,
        "get_operation_definition",
        lambda _key: SimpleNamespace(
            result_mode="dataset",
            dataset_kind="customers_without_fair",
            script_path=None,
        ),
    )

    builder_called = False

    def builder(*args, **kwargs):
        nonlocal builder_called
        builder_called = True
        raise AssertionError("dataset builder must not start after suspension is observed")

    monkeypatch.setitem(runner_module._DATASET_BUILDERS, "customers_without_fair", builder)

    checkpoint_calls = 0

    def checkpoint() -> None:
        nonlocal checkpoint_calls
        checkpoint_calls += 1
        if checkpoint_calls >= 2:
            raise RunningWorkLifecycleCancelledError(
                organization_id=organization_id,
                status="suspended",
            )

    runner = DataOperationJobRunner(
        session_factory=lambda: session,  # type: ignore[arg-type]
        enforce_lifecycle=True,
        lifecycle_checkpoint_factory=lambda _organization_id: checkpoint,
    )
    runner.run_operation(
        DataOperationJobCommand(
            organization_id=organization_id,
            run_id=run.id,
        )
    )

    assert checkpoint_calls == 2
    assert builder_called is False
    assert session.rollbacks >= 1
    assert session.closed is True
    assert run.status == DataOperationRunStatus.CANCELLED
    assert "suspended" in (run.error_message or "")
