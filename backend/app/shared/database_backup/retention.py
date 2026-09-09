"""Operational retention enforcement for FAIR CRM full database backups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.system_admin.domain.value_objects import SystemBackupStatus
from app.modules.system_admin.infrastructure.persistence.models import SystemBackupModel
from app.shared.database_backup.database_keys import DatabaseKey
from app.shared.database_backup.formats import BackupFormat
from app.shared.database_backup.paths import resolve_backup_path


@dataclass(frozen=True, slots=True)
class BackupRetentionPruneResult:
    cutoff: datetime
    deleted_count: int
    failed_count: int


def prune_expired_fair_crm_full_backups(
    *,
    session: Session | None = None,
    now: datetime | None = None,
    retention_days: int | None = None,
) -> BackupRetentionPruneResult:
    """Delete expired FAIR CRM full backup artifacts and their metadata.

    Successful ``completed_at`` is the only age origin. Universal data packages are
    not full database backups and are intentionally outside the OL10 full-DB policy.
    A file deletion failure leaves its metadata row intact so the next pass can
    retry instead of falsely recording the backup as removed.
    """

    settings = get_settings()
    days = retention_days or settings.database_backup_retention_days
    current_time = now or datetime.now(tz=UTC)
    cutoff = current_time - timedelta(days=days)
    owns_session = session is None
    db = session or SessionLocal()
    deleted_count = 0
    failed_count = 0

    try:
        expired = (
            db.query(SystemBackupModel)
            .filter(
                SystemBackupModel.database_key == DatabaseKey.FAIR_CRM.value,
                SystemBackupModel.status == SystemBackupStatus.COMPLETED.value,
                SystemBackupModel.completed_at.isnot(None),
                SystemBackupModel.completed_at < cutoff,
                SystemBackupModel.backup_format.in_(
                    [
                        BackupFormat.POSTGRESQL_DUMP.value,
                        BackupFormat.POSTGRESQL_SQL.value,
                    ]
                ),
            )
            .order_by(SystemBackupModel.completed_at.asc())
            .all()
        )

        for model in expired:
            try:
                resolve_backup_path(model.file_name).unlink(missing_ok=True)
            except (OSError, ValueError):
                failed_count += 1
                continue
            db.delete(model)
            deleted_count += 1

        db.commit()
        return BackupRetentionPruneResult(
            cutoff=cutoff,
            deleted_count=deleted_count,
            failed_count=failed_count,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()
