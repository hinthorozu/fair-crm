"""P0.1 tenant-isolation evidence for organization-owned background jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import sessionmaker

from app.modules.data_integration.application.import_job_runner import (
    AnalyzeJobCommand,
    ImportJobRunner,
)
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.infrastructure.repositories.job_repository import (
    SqlAlchemyImportJobRepository,
)
from app.modules.fair_emails.application.commands import ProcessBatchCommand
from app.modules.fair_emails.application.process_batch import ProcessFairEmailBatchUseCase
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailBatchModel
from app.modules.imports.domain.value_objects import ImportJobStatus
from app.modules.system_admin.application.data_operation_job_runner import (
    DataOperationJobCommand,
    DataOperationJobRunner,
)
from app.modules.system_admin.domain.data_operation_entities import DataOperationRun
from app.modules.system_admin.domain.data_operation_value_objects import DataOperationRunStatus
from app.modules.system_admin.infrastructure.repositories.data_operation_run_repository import (
    SqlAlchemyDataOperationRunRepository,
)


def _session_factory(db_session):
    return sessionmaker(bind=db_session.bind)


def test_import_job_runner_rejects_foreign_job_before_state_change(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    now = datetime.now(tz=UTC)
    job_repo = SqlAlchemyImportJobRepository(db_session)
    job = job_repo.add(
        ImportJob.create_analyze_job(
            organization_id=owner_org,
            batch_id=uuid4(),
            progress_total=1,
            now=now,
        )
    )
    db_session.commit()

    ImportJobRunner(session_factory=_session_factory(db_session)).run_analyze(
        AnalyzeJobCommand(
            organization_id=foreign_org,
            user_id=uuid4(),
            access_token="background-job-tenant-test",
            batch_id=job.batch_id,
            job_id=job.id,
        )
    )

    db_session.expire_all()
    unchanged = job_repo.get_by_id(owner_org, job.id)
    assert unchanged is not None
    assert unchanged.status == ImportJobStatus.QUEUED
    assert unchanged.started_at is None
    assert unchanged.completed_at is None
    assert unchanged.error_message is None


def test_data_operation_job_runner_rejects_foreign_run_before_state_change(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    now = datetime.now(tz=UTC)
    run_repo = SqlAlchemyDataOperationRunRepository(db_session)
    run = run_repo.add(
        DataOperationRun.create(
            organization_id=owner_org,
            operation_key="duplicate_customer_analysis",
            started_by=uuid4(),
            started_by_email="tenant-test@example.com",
            now=now,
        )
    )
    db_session.commit()

    DataOperationJobRunner(session_factory=_session_factory(db_session)).run_operation(
        DataOperationJobCommand(
            organization_id=foreign_org,
            run_id=run.id,
        )
    )

    db_session.expire_all()
    unchanged = run_repo.get_by_id(owner_org, run.id)
    assert unchanged is not None
    assert unchanged.status == DataOperationRunStatus.QUEUED
    assert unchanged.completed_at is None
    assert unchanged.error_message is None


def test_mail_batch_worker_rejects_foreign_batch_before_state_change(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    now = datetime.now(tz=UTC)
    batch = FairEmailBatchModel(
        id=uuid4(),
        organization_id=owner_org,
        fair_id=None,
        operation_id=None,
        template_id=uuid4(),
        email_account_id=None,
        subject_override=None,
        recipient_options_json={},
        status="queued",
        total_count=0,
        sent_count=0,
        failed_count=0,
        skipped_count=0,
        created_by_user_id=uuid4(),
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    db_session.add(batch)
    db_session.commit()

    ProcessFairEmailBatchUseCase(db_session).execute(
        ProcessBatchCommand(
            batch_id=batch.id,
            organization_id=foreign_org,
        )
    )

    db_session.expire_all()
    unchanged = db_session.get(FairEmailBatchModel, batch.id)
    assert unchanged is not None
    assert unchanged.organization_id == owner_org
    assert unchanged.status == "queued"
    assert unchanged.sent_count == 0
    assert unchanged.failed_count == 0
    assert unchanged.completed_at is None
