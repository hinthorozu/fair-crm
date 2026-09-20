"""Certified restore runner.

Restore is dump-then-migrate: pg_restore loads data, alembic upgrade head
brings the schema to the current code, then health checks fail closed.
Uploaded dumps are a supported off-machine path. Checksums and database-key
matching still apply; restore is not limited to backups tracked on this machine.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.integrations.kyrox_core.lifecycle import OrganizationLifecycleGuard
from app.integrations.kyrox_core.ports import AuditPort
from app.modules.system_admin.application import restore_job_service
from app.modules.system_admin.application.restore_job_service import (
    RestoreJobMaintenanceCommand,
    RestoreJobMaintenanceRunner,
)
from app.modules.system_admin.domain.entities import SystemBackup, SystemBackupRestoreJob
from app.modules.system_admin.domain.value_objects import RestoreJobSourceType, SystemBackupStatus
from app.modules.system_admin.infrastructure.repositories.backup_repository import (
    SqlAlchemySystemBackupRepository,
)
from app.modules.system_admin.infrastructure.repositories.restore_job_repository import (
    SqlAlchemySystemBackupRestoreJobRepository,
)
from app.shared.database_backup.core_restore_lifecycle import (
    CoreRestoreLifecycleReconciliationResult,
    capture_core_restore_lifecycle_snapshot,
    reconcile_core_restore_lifecycle,
)
from app.shared.database_backup.database_keys import DatabaseKey
from app.shared.database_backup.formats import BackupFormat
from app.shared.database_backup.restore_reconciliation import (
    RestoreOrganizationReconciliationResult,
    run_restore_organization_reconciliation,
)

RestoreReconciliationResult = (
    RestoreOrganizationReconciliationResult | CoreRestoreLifecycleReconciliationResult
)


@dataclass(frozen=True, slots=True)
class CertifiedPostRestoreHealthResult:
    base_health: object
    reconciliation: RestoreReconciliationResult

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


def validate_restore_source_provenance(
    *,
    job: SystemBackupRestoreJob,
    backup: SystemBackup | None,
    dump_path: Path,
    checksum_file: Callable[[Path], str],
) -> None:
    """Confirm the restore dump matches the job.

    Restore eligibility is not "this machine's Admin backup row". USB / uploaded
    dumps are valid when they are a PostgreSQL dump for the selected database
    and the stored checksum still matches. Tracked list restores additionally
    check file name, format and completion. Schema compatibility is not proven
    here; alembic upgrade head after pg_restore is the schema control.
    """

    if job.source_database_key != job.target_database_key:
        raise ValueError("Cross-database restore is not permitted")

    if job.source_type == RestoreJobSourceType.UPLOADED_FILE:
        if job.backup_id is not None or backup is not None:
            raise ValueError("Uploaded restore must not reference a tracked backup")
        if not job.checksum_sha256:
            raise ValueError("Restore source is missing authoritative checksum provenance")
        actual_checksum = checksum_file(dump_path)
        if actual_checksum != job.checksum_sha256:
            raise ValueError("Restore dump checksum no longer matches uploaded restore provenance")
        return

    if job.source_type != RestoreJobSourceType.EXISTING_BACKUP:
        raise ValueError("Unsupported restore source type")
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
    if backup.file_name != job.source_file_name:
        raise ValueError("Restore source file does not match tracked backup provenance")
    if not backup.checksum or not job.checksum_sha256:
        raise ValueError("Restore source is missing authoritative checksum provenance")
    if backup.checksum != job.checksum_sha256:
        raise ValueError("Restore job checksum does not match tracked backup provenance")

    actual_checksum = checksum_file(dump_path)
    if actual_checksum != backup.checksum:
        raise ValueError("Restore dump checksum no longer matches tracked backup provenance")


class CertifiedRestoreJobMaintenanceRunner:
    """Execute dump restore, then current-schema migrations and health checks."""

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
        original_checksum = (
            restore_job_service.sha256_file
            if hasattr(restore_job_service, "sha256_file")
            else None
        )
        core_snapshot_json: str | None = None

        # sha256_file is defined in the backup engine, while restore_job_service historically
        # did not import it. Import locally so the existing module stays untouched.
        from app.shared.database_backup.engine import sha256_file

        def certified_verify_backup_dump(*, database_url: str, dump_path: Path):
            nonlocal core_snapshot_json
            if job is not None:
                validate_restore_source_provenance(
                    job=job,
                    backup=backup,
                    dump_path=dump_path,
                    checksum_file=sha256_file,
                )
            verification = original_verify(database_url=database_url, dump_path=dump_path)
            if job is not None and job.target_database_key == DatabaseKey.KYROX_CORE:
                # Capture current Core lifecycle truth only after dump verification and
                # immediately before the base runner releases connections for pg_restore.
                # The snapshot remains in this maintenance process memory and therefore
                # is not overwritten with the Core database.
                core_snapshot_json = capture_core_restore_lifecycle_snapshot(
                    database_url=database_url
                )
            return verification

        def certified_post_restore_health_check(**kwargs):
            base_health = original_health(**kwargs)
            if not base_health.ok:
                return base_health

            database_key = DatabaseKey(kwargs["database_key"])
            if database_key == DatabaseKey.KYROX_CORE:
                reconciliation: RestoreReconciliationResult = (
                    reconcile_core_restore_lifecycle(
                        database_url=kwargs["database_url"],
                        snapshot_json=core_snapshot_json,
                    )
                )
            elif database_key == DatabaseKey.FAIR_STAND:
                return base_health
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
