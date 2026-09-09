from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.modules.system_admin.domain.entities import SystemBackup
from app.modules.system_admin.domain.value_objects import SystemBackupStage, SystemBackupStatus
from app.modules.system_admin.infrastructure.repositories.backup_repository import (
    SqlAlchemySystemBackupRepository,
)
from app.shared.database_backup.database_keys import DatabaseKey
from app.shared.database_backup.formats import BackupFormat
from app.shared.database_backup.retention import prune_expired_fair_crm_full_backups


def _completed_backup(
    *,
    organization_id: UUID,
    completed_at: datetime,
    backup_format: BackupFormat = BackupFormat.POSTGRESQL_DUMP,
) -> SystemBackup:
    extension = ".sql" if backup_format == BackupFormat.POSTGRESQL_SQL else ".dump"
    return SystemBackup(
        id=uuid4(),
        organization_id=organization_id,
        database_key=DatabaseKey.FAIR_CRM,
        file_name=f"fair_crm_backup_{uuid4().hex}{extension}",
        backup_format=backup_format,
        file_size=10,
        status=SystemBackupStatus.COMPLETED,
        progress_stage=SystemBackupStage.COMPLETED,
        started_at=completed_at - timedelta(minutes=1),
        completed_at=completed_at,
        duration_seconds=60,
        created_by=uuid4(),
        created_by_email="owner@example.com",
        notes=None,
        checksum="b" * 64,
        manifest_json=None,
        download_count=0,
        error_message=None,
        created_at=completed_at,
        updated_at=completed_at,
    )


def test_retention_prunes_backup_older_than_30_days(
    db_session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    organization_id = uuid4()
    backup = _completed_backup(
        organization_id=organization_id,
        completed_at=now - timedelta(days=30, seconds=1),
    )
    repo = SqlAlchemySystemBackupRepository(db_session)
    repo.add(backup)
    db_session.commit()

    backup_path = tmp_path / backup.file_name
    backup_path.write_bytes(b"PGDMP-test")
    monkeypatch.setattr(
        "app.shared.database_backup.retention.resolve_backup_path",
        lambda file_name: tmp_path / file_name,
    )

    result = prune_expired_fair_crm_full_backups(
        session=db_session,
        now=now,
        retention_days=30,
    )

    assert result.deleted_count == 1
    assert result.failed_count == 0
    assert backup_path.exists() is False
    assert repo.get_by_id(organization_id, backup.id) is None


def test_retention_keeps_exact_30_day_boundary(
    db_session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    organization_id = uuid4()
    backup = _completed_backup(
        organization_id=organization_id,
        completed_at=now - timedelta(days=30),
    )
    repo = SqlAlchemySystemBackupRepository(db_session)
    repo.add(backup)
    db_session.commit()

    backup_path = tmp_path / backup.file_name
    backup_path.write_bytes(b"PGDMP-test")
    monkeypatch.setattr(
        "app.shared.database_backup.retention.resolve_backup_path",
        lambda file_name: tmp_path / file_name,
    )

    result = prune_expired_fair_crm_full_backups(
        session=db_session,
        now=now,
        retention_days=30,
    )

    assert result.deleted_count == 0
    assert backup_path.exists() is True
    assert repo.get_by_id(organization_id, backup.id) is not None
