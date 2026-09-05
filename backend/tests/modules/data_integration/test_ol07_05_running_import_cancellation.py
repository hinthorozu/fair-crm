from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.modules.data_integration.application import import_job_runner as runner_module
from app.modules.data_integration.application.import_job_runner import ApplyJobCommand, ImportJobRunner
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.imports.domain.entities import ImportBatch
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportJobStatus
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


class _JobRepo:
    def __init__(self, job: ImportJob) -> None:
        self.job = job

    def get_by_id(self, organization_id, job_id):
        if self.job.organization_id == organization_id and self.job.id == job_id:
            return self.job
        return None

    def update(self, job):
        self.job = job
        return job


class _BatchRepo:
    def __init__(self, batch: ImportBatch) -> None:
        self.batch = batch

    def get_by_id(self, organization_id, batch_id):
        if self.batch.organization_id == organization_id and self.batch.id == batch_id:
            return self.batch
        return None

    def update(self, batch):
        self.batch = batch
        return batch


class _ApplyUseCase:
    def __init__(self, *args, progress_checkpoint=None, **kwargs) -> None:
        self.progress_checkpoint = progress_checkpoint


class _Executor:
    def __init__(self, use_case: _ApplyUseCase) -> None:
        self.use_case = use_case

    def execute(self, command):
        assert self.use_case.progress_checkpoint is not None
        self.use_case.progress_checkpoint()
        raise AssertionError("checkpoint should have cancelled before apply continued")


def test_running_apply_suspension_rolls_back_and_terminalizes_job_and_batch(monkeypatch):
    now = datetime.now(tz=UTC)
    organization_id = uuid4()
    batch = ImportBatch.create(
        organization_id=organization_id,
        fair_id=uuid4(),
        file_name="ol07.xlsx",
        now=now,
    )
    job = ImportJob.create_apply_job(
        organization_id=organization_id,
        batch_id=batch.id,
        progress_total=2,
        now=now,
    )
    session = _Session()
    job_repo = _JobRepo(job)
    batch_repo = _BatchRepo(batch)

    monkeypatch.setattr(runner_module, "SqlAlchemyImportJobRepository", lambda _db: job_repo)
    monkeypatch.setattr(runner_module, "SqlAlchemyImportBatchRepository", lambda _db: batch_repo)
    monkeypatch.setattr(runner_module, "SqlAlchemyImportRowRepository", lambda _db: SimpleNamespace())
    monkeypatch.setattr(runner_module, "LifecycleAwareApplyImportUseCase", _ApplyUseCase)
    monkeypatch.setattr(runner_module, "ImportExecutor", _Executor)
    monkeypatch.setattr(runner_module, "_communication_sync", lambda _db: SimpleNamespace())
    monkeypatch.setattr(runner_module, "SqlAlchemyCustomerRepository", lambda _db: SimpleNamespace())
    monkeypatch.setattr(runner_module, "SqlAlchemyContactRepository", lambda _db: SimpleNamespace())
    monkeypatch.setattr(runner_module, "SqlAlchemyActivityRepository", lambda _db: SimpleNamespace())
    monkeypatch.setattr(runner_module, "SqlAlchemyParticipationRepository", lambda _db: SimpleNamespace())
    monkeypatch.setattr(runner_module, "dev_bypass_enabled", lambda: True)

    checkpoint_calls = 0

    def checkpoint() -> None:
        nonlocal checkpoint_calls
        checkpoint_calls += 1
        if checkpoint_calls >= 2:
            raise RunningWorkLifecycleCancelledError(
                organization_id=organization_id,
                status="suspended",
            )

    runner = ImportJobRunner(
        session_factory=lambda: session,  # type: ignore[arg-type]
        enforce_lifecycle=True,
        lifecycle_checkpoint_factory=lambda _organization_id: checkpoint,
    )
    runner._run_apply(
        ApplyJobCommand(
            organization_id=organization_id,
            user_id=uuid4(),
            access_token="test",
            batch_id=batch.id,
            job_id=job.id,
        )
    )

    assert checkpoint_calls == 2
    assert session.rollbacks >= 1
    assert session.closed is True
    assert job.status == ImportJobStatus.CANCELLED
    assert batch.status == ImportBatchStatus.CANCELLED
    assert "suspended" in (job.error_message or "")
