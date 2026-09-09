"""OL10-certified restore runner.

This wrapper inserts fail-closed source-provenance and organization-lifecycle
checks into the existing destructive restore runner without weakening its current
pg_restore, migration, health, job-state, or audit behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.integrations.kyrox_core.ports import AuditPort
from app.modules.system_admin.application import restore_job_service
from app.modules.system_admin.application.restore_job_service import (
    RestoreJobMaintenanceCommand,
    RestoreJobMaintenanceRunner,
    resolve_restore_job_dump_path,
)
from app.modules.system_admin.domain.entities import SystemBackup, SystemBackupRestoreJob
from app.modules.system_admin.domain.value_objects import RestoreJobSourceType, SystemBackupStatus
from app.modules.system_admin.infrastructure.repositories.backup_repository import (
    SqlAlchemySystemBackupRepository,
)
from app.modules.system_admin.infrastructure.repositories.restore_job_repository import (
    SqlAlchemySystemBackupRestoreJobRepository,
)
from app.shared.database_backup.database_keys import DatabaseKey
from app.shared.database_backup.formats import BackupFormat
from app.shared.database_backup.restore_reconciliation import (
    RestoreOrganizationReconciliationResult,
    run_restore_organization_reconciliation,
)


@dataclass(frozen=True, slots=True)
class CertifiedPostRestoreHealthResult:
    base_health: object
    reconciliation: RestoreOrganizationReconciliationResult

    @property
    def ok(self) -> bool:
        return bool(getattr(self.base_health, "ok", False)) and self.reconciliation.ok

    @property
    def error_message(self) -> str | None:
        if not bool(getattr(self.base_health, "ok", False)):
            return getattr(self.base_health, "error_message", None)
        return self.reconciliation.error_message

    def log_lines(self) -> list[str]:
        base_lines = list(getattr(self.base_health, "log_lines")())
        return [*base_lines, *self.reconciliation.log_lines()]

    def summary_text(self) -> str:
        base_summary = str(getattr(self.base_health, "summary_text")())
        return f"{base_summary}\n{self.reconciliation.summary_text()}"


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def validate_restore_source_provenance(
    *,
    job: SystemBackupRestoreJob,
    backup: SystemBackup | None,
    dump_path: Path,
    now: datetime,
    retention_days: int,
    checksum_file: Callable[[Path], str],
) -> None:
    """Reject restore sources whose age or provenance cannot be established."""

    if job.target_database_key != DatabaseKey.FAIR_CRM:
        raise ValueError(
            "Kyrox Core restore is blocked in the FAIR CRM runner. Core restores require "
            "the Core-owned self-reconciliation path."
        )
    if job.source_type != RestoreJobSourceType.EXISTING_BACKUP:
        raise ValueError(
            "Uploaded restore source blocked: authoritative backup completion provenance "
            "is unavailable. Restore a tracked FAIR CRM backup instead."
        )
    if job.backup_id is None or backup is None:
        raise ValueError("Tracked restore backup provenance could not be resolved")
    if backup.id != job.backup_id or backup.organization_id != job.organization_id:
        raise ValueError("Restore backup provenance does not match the restore job")
    if backup.status != SystemBackupStatus.COMPLETED:
        raise ValueError("Only successfully completed backups may be restored")
    if backup.completed_at is None:
        raise ValueError("Completed backup is missing authoritative completed_at")
    if backup.backup_format != BackupFormat.POSTGRESQL_DUMP:
        raise ValueError("Only PostgreSQL custom dump backups may be restored")
    if backup.database_key != job.source_database_key:
        raise ValueError("Restore source database does not match tracked backup provenance")
    if job.source_database_key != job.target_database_key:
        raise ValueError("Cross-database restore is not permitted")
    if backup.file_name != job.source_file_name:
        raise ValueError("Restore source file does not match tracked backup provenance")
    if not backup.checksum or not job.checksum_sha256:
        raise ValueError("Restore source is missing authoritative checksum provenance")
    if backup.checksum != job.checksum_sha256:
        raise ValueError("Restore job checksum does not match tracked backup provenance")

    completed_at = _ensure_utc(backup.completed_at)
    current_time = _ensure_utc(now)
    if completed_at > current_time:
        raise ValueError("Backup completed_at is in the future")
    if current_time - completed_at > timedelta(days=retention_days):
        raise ValueError(
            f"Backup is older than the {retention_days}-day restore retention limit"
        )

    actual_checksum = checksum_file(dump_path)
    if actual_checksum != backup.checksum:
        raise ValueError("Restore dump checksum no longer matches tracked backup provenance")


class CertifiedRestoreJobMaintenanceRunner:
    """Execute the existing restore flow with OL10 certification gates."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
        audit: AuditPort | None = None,
        lifecycle_guard: OrganizationLifecycleGuard | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._base_session_factory = session_factory
        self._audit = audit
        self._lifecycle_guard = lifecycle_guard or OrganizationLifecycleGuard()
        self._now_provider = now_provider or (lambda: datetime.now(tz=UTC))

    def run(self, command: RestoreJobMaintenanceCommand) -> int:
        # Resolve immutable job/source provenance before pg_restore can overwrite DB state.
        db = self._session_factory()
        try:
            job_repository = SqlAlchemySystemBackupRestoreJobRepository(db)
            job = job_repository.get_by_id_global(command.job_id)
            backup = None
            if job is not None and job.backup_id is not None:
                backup = SqlAlchemySystemBackupRepository(db).get_by_id(
                    job.organization_id,
                    job.backup_id,
                )
        finally:
            db.close()

        original_verify = restore_job_service.verify_backup_dump
        original_health = restore_job_service.run_post_restore_health_check
        original_checksum = restore_job_service.sha256_file if hasattr(restore_job_service, "sha256_file") else None

        # sha256_file is defined in the backup engine, while restore_job_service historically
        # did not import it. Import locally so the existing module stays untouched.
        from app.shared.database_backup.engine import sha256_file

        def certified_verify_backup_dump(*, database_url: str, dump_path: Path):
            if job is not None:
                settings = get_settings()
                validate_restore_source_provenance(
                    job=job,
                    backup=backup,
                    dump_path=dump_path,
                    now=self._now_provider(),
                    retention_days=settings.database_backup_retention_days,
                    checksum_file=sha256_file,
                )
            return original_verify(database_url=database_url, dump_path=dump_path)

        def certified_post_restore_health_check(**kwargs):
            base_health = original_health(**kwargs)
            if not base_health.ok:
                return base_health

            database_key = DatabaseKey(kwargs["database_key"])
            if database_key != DatabaseKey.FAIR_CRM:
                reconciliation = RestoreOrganizationReconciliationResult(
                    ok=False,
                    organization_count=0,
                    active_count=0,
                    inactive_count=0,
                    deleted_count=0,
                    error_message=(
                        "Core restore requires Core-owned self-reconciliation and cannot be "
                        "certified by FAIR CRM"
                    ),
                )
            else:
                reconciliation = run_restore_organization_reconciliation(
                    database_url=kwargs["database_url"],
                    lifecycle_guard=self._lifecycle_guard,
                )
            return CertifiedPostRestoreHealthResult(
                base_health=base_health,
                reconciliation=reconciliation,
            )

        restore_job_service.verify_backup_dump = certified_verify_backup_dump
        restore_job_service.run_post_restore_health_check = certified_post_restore_health_check
        try:
            runner = RestoreJobMaintenanceRunner(
                session_factory=self._base_session_factory,
                audit=self._audit,
            )
            return runner.run(command)
        finally:
            restore_job_service.verify_backup_dump = original_verify
            restore_job_service.run_post_restore_health_check = original_health
            if original_checksum is not None:
                restore_job_service.sha256_file = original_checksum
