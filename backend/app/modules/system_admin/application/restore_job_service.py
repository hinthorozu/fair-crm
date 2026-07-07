from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.pagination import normalize_sort_direction
from app.db.session import SessionLocal
from app.integrations.kyrox_core.ports import AuditPort, AuthorizationPort
from app.modules.system_admin.domain.entities import SystemBackupRestoreJob
from app.modules.system_admin.domain.ports import SystemBackupRepository, SystemBackupRestoreJobRepository
from app.modules.system_admin.domain.value_objects import RestoreJobSourceType, RestoreJobStatus
from app.modules.system_admin.infrastructure.repositories.backup_repository import SqlAlchemySystemBackupRepository
from app.modules.system_admin.infrastructure.repositories.restore_job_repository import (
    SqlAlchemySystemBackupRestoreJobRepository,
)
from app.shared.database_backup.engine import (
    DatabaseBackupError,
    is_custom_pg_dump,
    pg_restore_custom,
    verify_backup_dump,
)
from app.shared.database_backup.paths import get_repo_root, get_restore_logs_dir, get_restore_uploads_dir, relative_repo_path, resolve_backup_path
from app.shared.database_backup.post_restore_health import run_post_restore_health_check

PERMISSION_READ = "fair_crm.admin.backups.read"

RESTORE_JOB_ALLOWED_SORT_FIELDS = frozenset(
    {
        "status",
        "source_type",
        "source_file_name",
        "requested_at",
        "requested_by_email",
        "notes",
        "created_at",
    }
)
RESTORE_JOB_DEFAULT_SORT_FIELD = "requested_at"
RESTORE_JOB_DEFAULT_SORT_DIRECTION = "desc"

RESTORE_JOB_MESSAGE = (
    "Restore job recorded. Automatic in-process restore is not production-safe; "
    "run scripts/dev/run-restore-job.ps1 against this job id."
)


@dataclass
class RestoreJobResult:
    id: UUID
    status: str
    source_type: str
    backup_id: UUID | None
    source_file_name: str
    checksum_sha256: str | None
    notes: str | None
    requested_by_user_id: UUID
    requested_by_email: str | None
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    restore_log_path: str | None
    message: str
    uploaded: bool
    backup_file_name: str | None = None
    backup_format: str | None = None


def _to_result(job: SystemBackupRestoreJob, *, backup_file_name: str | None = None, backup_format: str | None = None) -> RestoreJobResult:
    return RestoreJobResult(
        id=job.id,
        status=job.status.value,
        source_type=job.source_type.value,
        backup_id=job.backup_id,
        source_file_name=job.source_file_name,
        checksum_sha256=job.checksum_sha256,
        notes=job.notes,
        requested_by_user_id=job.requested_by_user_id,
        requested_by_email=job.requested_by_email,
        requested_at=job.requested_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        failed_at=job.failed_at,
        error_message=job.error_message,
        restore_log_path=job.restore_log_path,
        message=RESTORE_JOB_MESSAGE,
        uploaded=job.source_type == RestoreJobSourceType.UPLOADED_FILE,
        backup_file_name=backup_file_name,
        backup_format=backup_format,
    )


class ListRestoreJobsUseCase:
    def __init__(
        self,
        repository: SystemBackupRestoreJobRepository,
        backup_repository: SystemBackupRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._repository = repository
        self._backup_repository = backup_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        page: int,
        page_size: int,
        sort_by: str = RESTORE_JOB_DEFAULT_SORT_FIELD,
        sort_dir: str = RESTORE_JOB_DEFAULT_SORT_DIRECTION,
    ) -> tuple[list[RestoreJobResult], int, str, str]:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Permission denied")

        resolved_sort = (
            sort_by if sort_by in RESTORE_JOB_ALLOWED_SORT_FIELDS else RESTORE_JOB_DEFAULT_SORT_FIELD
        )
        resolved_dir = normalize_sort_direction(sort_dir or RESTORE_JOB_DEFAULT_SORT_DIRECTION)
        items, total = self._repository.list_recent(
            organization_id,
            page=page,
            page_size=page_size,
            sort_by=resolved_sort,
            sort_dir=resolved_dir,
        )
        results = []
        for job in items:
            backup_file_name = None
            backup_format = None
            if job.backup_id is not None:
                backup = self._backup_repository.get_by_id(organization_id, job.backup_id)
                if backup is not None:
                    backup_file_name = backup.file_name
                    backup_format = backup.backup_format.value
            results.append(
                _to_result(job, backup_file_name=backup_file_name, backup_format=backup_format)
            )
        return results, total, resolved_sort, resolved_dir


class GetRestoreJobUseCase:
    def __init__(
        self,
        repository: SystemBackupRestoreJobRepository,
        backup_repository: SystemBackupRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._repository = repository
        self._backup_repository = backup_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        job_id: UUID,
    ) -> RestoreJobResult:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Permission denied")

        job = self._repository.get_by_id(organization_id, job_id)
        if job is None:
            raise LookupError("Restore job not found")

        backup_file_name = None
        backup_format = None
        if job.backup_id is not None:
            backup = self._backup_repository.get_by_id(organization_id, job.backup_id)
            if backup is not None:
                backup_file_name = backup.file_name
                backup_format = backup.backup_format.value
        return _to_result(job, backup_file_name=backup_file_name, backup_format=backup_format)


def resolve_restore_job_dump_path(job: SystemBackupRestoreJob) -> Path:
    if job.source_type == RestoreJobSourceType.EXISTING_BACKUP:
        if job.backup_id is None:
            raise ValueError("Restore job is missing backup reference")
        return resolve_backup_path(job.source_file_name)
    if not job.uploaded_file_path:
        raise ValueError("Restore job is missing uploaded file path")
    candidate = (get_repo_root() / job.uploaded_file_path).resolve()
    uploads_root = get_restore_uploads_dir().resolve()
    if uploads_root not in candidate.parents and candidate != uploads_root:
        raise ValueError("Uploaded restore path escapes restore uploads directory")
    return candidate


def _merge_restore_job_notes(existing: str | None, health_summary: str) -> str:
    if existing and existing.strip():
        return f"{existing.strip()}\n\n{health_summary}"
    return health_summary


@dataclass(frozen=True)
class RestoreJobMaintenanceCommand:
    job_id: UUID
    target_database_url: str
    allow_restore: bool


class RestoreJobMaintenanceRunner:
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        audit: AuditPort | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._audit = audit

    def run(self, command: RestoreJobMaintenanceCommand) -> int:
        if not command.allow_restore:
            print("Restore blocked: set ALLOW_RESTORE=true to run destructive restore.", file=sys.stderr)
            return 1
        if not command.target_database_url.strip():
            print("Restore blocked: TARGET_DATABASE_URL is required.", file=sys.stderr)
            return 1

        db = self._session_factory()
        log_handle = None
        try:
            repo = SqlAlchemySystemBackupRestoreJobRepository(db)
            job = repo.get_by_id_global(command.job_id)
            if job is None:
                print(f"Restore job not found: {command.job_id}", file=sys.stderr)
                return 1
            if job.status != RestoreJobStatus.MANUAL_RESTORE_REQUIRED:
                print(
                    f"Restore job status must be manual_restore_required (current: {job.status.value})",
                    file=sys.stderr,
                )
                return 1

            logs_dir = get_restore_logs_dir()
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = logs_dir / f"{job.id}.log"
            relative_log_path = relative_repo_path(log_path)
            now = datetime.now(tz=UTC)
            job.mark_running(now=now, restore_log_path=relative_log_path)
            repo.update(job)
            db.commit()

            log_handle = log_path.open("a", encoding="utf-8")

            def _log(message: str) -> None:
                print(message)
                if log_handle:
                    log_handle.write(message + "\n")
                    log_handle.flush()

            self._record_audit(
                organization_id=job.organization_id,
                action="fair_crm.system_backup.restore_started",
                job=job,
                metadata={"runner": "maintenance_script"},
            )

            dump_path = resolve_restore_job_dump_path(job)
            _log(f"Restore job: {job.id}")
            _log(f"Source type: {job.source_type.value}")
            _log(f"Dump file: {dump_path}")

            if not dump_path.exists():
                raise FileNotFoundError(f"Dump file not found: {dump_path}")
            if not is_custom_pg_dump(dump_path):
                raise ValueError("Dump file is not PostgreSQL custom format")

            verify_backup_dump(database_url=command.target_database_url, dump_path=dump_path)
            _log("Dump validation OK")

            pg_restore_custom(database_url=command.target_database_url, dump_path=dump_path)
            _log("pg_restore completed")

            repo_root = get_repo_root()
            _log("Running alembic upgrade head")
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if log_handle:
                if result.stdout:
                    log_handle.write(result.stdout)
                if result.stderr:
                    log_handle.write(result.stderr)
                log_handle.flush()
            if result.returncode != 0:
                raise DatabaseBackupError(result.stderr or result.stdout or "alembic upgrade head failed")
            _log("Alembic upgrade head completed")

            health = run_post_restore_health_check(
                database_url=command.target_database_url,
                migration_result="success",
            )
            for line in health.log_lines():
                _log(line)
            if not health.ok:
                raise ValueError(health.error_message or "Post-restore health check failed")

            finished = datetime.now(tz=UTC)
            job = repo.get_by_id_global(command.job_id)
            if job is None:
                return 1
            job.notes = _merge_restore_job_notes(job.notes, health.summary_text())
            job.mark_completed(now=finished)
            repo.update(job)
            db.commit()

            self._record_audit(
                organization_id=job.organization_id,
                action="fair_crm.system_backup.restore_completed",
                job=job,
                metadata={"runner": "maintenance_script", "restore_log_path": relative_log_path},
            )
            _log("Restore job completed")
            return 0
        except (DatabaseBackupError, OSError, ValueError, FileNotFoundError) as exc:
            db.rollback()
            failed = datetime.now(tz=UTC)
            repo = SqlAlchemySystemBackupRestoreJobRepository(db)
            job = repo.get_by_id_global(command.job_id)
            if job is not None:
                job.mark_failed(error_message=str(exc), now=failed)
                repo.update(job)
                db.commit()
                self._record_audit(
                    organization_id=job.organization_id,
                    action="fair_crm.system_backup.restore_failed",
                    job=job,
                    metadata={"runner": "maintenance_script", "error": str(exc)},
                )
            print(f"Restore failed: {exc}", file=sys.stderr)
            if log_handle:
                log_handle.write(f"Restore failed: {exc}\n")
                log_handle.flush()
            return 1
        finally:
            if log_handle:
                log_handle.close()
            db.close()

    def _record_audit(
        self,
        *,
        organization_id: UUID,
        action: str,
        job: SystemBackupRestoreJob,
        metadata: dict | None = None,
    ) -> None:
        if self._audit is None:
            return
        self._audit.record_event(
            organization_id=organization_id,
            access_token="",
            action=action,
            resource_type="system_backup_restore_job",
            resource_id=str(job.id),
            new_values={
                "status": job.status.value,
                "source_type": job.source_type.value,
                "source_file_name": job.source_file_name,
            },
            metadata={
                "requested_by_user_id": str(job.requested_by_user_id),
                **(metadata or {}),
            },
        )
