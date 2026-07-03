"""Tests for import job activity detection."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.data_integration.domain.entities import ImportJob
from app.modules.imports.domain.services.import_job_activity import is_import_job_active_for_batch
from app.modules.imports.domain.value_objects import ImportJobStatus, ImportJobType


def _apply_job(status: ImportJobStatus) -> ImportJob:
    now = datetime.now(tz=UTC)
    job = ImportJob.create_apply_job(
        organization_id=uuid4(),
        batch_id=uuid4(),
        progress_total=1,
        now=now,
    )
    job.status = status
    return job


def test_queued_apply_job_inactive_when_batch_analyzed():
    assert is_import_job_active_for_batch("analyzed", _apply_job(ImportJobStatus.QUEUED)) is False


def test_queued_apply_job_active_when_batch_applying():
    assert is_import_job_active_for_batch("applying", _apply_job(ImportJobStatus.QUEUED)) is True


def test_running_apply_job_always_active():
    assert is_import_job_active_for_batch("analyzed", _apply_job(ImportJobStatus.RUNNING)) is True


def test_completed_apply_job_inactive():
    assert is_import_job_active_for_batch("applying", _apply_job(ImportJobStatus.COMPLETED)) is False
