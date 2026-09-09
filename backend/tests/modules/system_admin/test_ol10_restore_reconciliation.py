from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Column, MetaData, String, Table, create_engine

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleSnapshot,
    OrganizationLifecycleUnavailableError,
)
from app.modules.system_admin.domain.entities import SystemBackup, SystemBackupRestoreJob
from app.modules.system_admin.domain.value_objects import (
    RestoreJobSourceType,
    SystemBackupStage,
    SystemBackupStatus,
)
from app.modules.system_admin.maintenance.certified_restore_runner import (
    validate_restore_source_provenance,
)
from app.shared.database_backup.database_keys import DatabaseKey
from app.shared.database_backup.formats import BackupFormat
from app.shared.database_backup.restore_reconciliation import (
    enumerate_restored_organization_ids,
    run_restore_organization_reconciliation,
)

_EPISODE_AT = datetime(2026, 9, 9, 16, 0, tzinfo=UTC)


def _backup(
    *,
    organization_id: UUID,
    completed_at: datetime,
    database_key: DatabaseKey = DatabaseKey.FAIR_CRM,
) -> SystemBackup:
    now = completed_at
    return SystemBackup(
        id=uuid4(),
        organization_id=organization_id,
        database_key=database_key,
        file_name=f"{database_key.value}_backup_test.dump",
        backup_format=BackupFormat.POSTGRESQL_DUMP,
        file_size=123,
        status=SystemBackupStatus.COMPLETED,
        progress_stage=SystemBackupStage.COMPLETED,
        started_at=completed_at - timedelta(minutes=5),
        completed_at=completed_at,
        duration_seconds=300,
        created_by=uuid4(),
        created_by_email="owner@example.com",
        notes=None,
        checksum="a" * 64,
        manifest_json=None,
        download_count=0,
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def _restore_job(*, backup: SystemBackup) -> SystemBackupRestoreJob:
    return SystemBackupRestoreJob.create(
        organization_id=backup.organization_id,
        source_type=RestoreJobSourceType.EXISTING_BACKUP,
        source_database_key=backup.database_key,
        target_database_key=backup.database_key,
        backup_id=backup.id,
        uploaded_file_path=None,
        source_file_name=backup.file_name,
        checksum_sha256=backup.checksum,
        notes=None,
        requested_by_user_id=uuid4(),
        requested_by_email="owner@example.com",
        now=backup.completed_at or datetime.now(tz=UTC),
    )


def test_restore_source_accepts_exact_30_day_boundary(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    backup = _backup(organization_id=uuid4(), completed_at=now - timedelta(days=30))
    job = _restore_job(backup=backup)
    dump_path = tmp_path / backup.file_name
    dump_path.write_bytes(b"PGDMP-test")

    validate_restore_source_provenance(
        job=job,
        backup=backup,
        dump_path=dump_path,
        now=now,
        retention_days=30,
        checksum_file=lambda _: "a" * 64,
    )


def test_restore_source_rejects_backup_older_than_30_days(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    backup = _backup(
        organization_id=uuid4(),
        completed_at=now - timedelta(days=30, seconds=1),
    )
    job = _restore_job(backup=backup)
    dump_path = tmp_path / backup.file_name
    dump_path.write_bytes(b"PGDMP-test")

    with pytest.raises(ValueError, match="older than the 30-day"):
        validate_restore_source_provenance(
            job=job,
            backup=backup,
            dump_path=dump_path,
            now=now,
            retention_days=30,
            checksum_file=lambda _: "a" * 64,
        )


def test_restore_source_rejects_uploaded_dump_without_authoritative_age(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    backup = _backup(organization_id=uuid4(), completed_at=now)
    job = _restore_job(backup=backup)
    job.source_type = RestoreJobSourceType.UPLOADED_FILE
    job.backup_id = None
    dump_path = tmp_path / "uploaded.dump"
    dump_path.write_bytes(b"PGDMP-test")

    with pytest.raises(ValueError, match="Uploaded restore source blocked"):
        validate_restore_source_provenance(
            job=job,
            backup=None,
            dump_path=dump_path,
            now=now,
            retention_days=30,
            checksum_file=lambda _: "a" * 64,
        )


def test_core_restore_requires_tracked_provenance_but_does_not_invent_fair_retention(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    backup = _backup(
        organization_id=uuid4(),
        completed_at=now - timedelta(days=365),
        database_key=DatabaseKey.KYROX_CORE,
    )
    job = _restore_job(backup=backup)
    dump_path = tmp_path / backup.file_name
    dump_path.write_bytes(b"PGDMP-test")

    validate_restore_source_provenance(
        job=job,
        backup=backup,
        dump_path=dump_path,
        now=now,
        retention_days=30,
        checksum_file=lambda _: "a" * 64,
    )


def _build_restored_sqlite(tmp_path: Path, organization_ids: list[UUID]) -> str:
    path = tmp_path / "restored.db"
    url = f"sqlite+pysqlite:///{path}"
    engine = create_engine(url)
    metadata = MetaData()
    customers = Table(
        "customers",
        metadata,
        Column("id", String, primary_key=True),
        Column("organization_id", String, nullable=False),
    )
    closures = Table(
        "organization_closure_records",
        metadata,
        Column("id", String, primary_key=True),
        Column("organization_id", String, nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        for index, organization_id in enumerate(organization_ids):
            connection.execute(
                customers.insert().values(
                    id=f"customer-{index}",
                    organization_id=str(organization_id),
                )
            )
        if organization_ids:
            connection.execute(
                closures.insert().values(
                    id="closure-0",
                    organization_id=str(organization_ids[0]),
                )
            )
    engine.dispose()
    return url


def test_candidate_enumeration_uses_all_organization_id_tables(tmp_path: Path) -> None:
    organization_ids = [uuid4(), uuid4()]
    url = _build_restored_sqlite(tmp_path, organization_ids)

    discovered = enumerate_restored_organization_ids(database_url=url)

    assert set(discovered) == set(organization_ids)


class _LifecycleGuard:
    def __init__(self, snapshots: dict[UUID, OrganizationLifecycleSnapshot]) -> None:
        self._snapshots = snapshots

    def get_snapshot(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        return self._snapshots[organization_id]


def test_reconciliation_accepts_active_and_suspended_non_deleted_orgs(tmp_path: Path) -> None:
    active_id = uuid4()
    suspended_id = uuid4()
    url = _build_restored_sqlite(tmp_path, [active_id, suspended_id])
    guard = _LifecycleGuard(
        {
            active_id: OrganizationLifecycleSnapshot(
                organization_id=active_id,
                status="active",
                work_allowed=True,
                updated_at=_EPISODE_AT,
            ),
            suspended_id: OrganizationLifecycleSnapshot(
                organization_id=suspended_id,
                status="suspended",
                work_allowed=False,
                updated_at=_EPISODE_AT,
            ),
        }
    )

    result = run_restore_organization_reconciliation(
        database_url=url,
        lifecycle_guard=guard,
    )

    assert result.ok is True
    assert result.organization_count == 2
    assert result.active_count == 1
    assert result.inactive_count == 1
    assert result.deleted_count == 0


def test_reconciliation_blocks_core_deleted_organization(tmp_path: Path) -> None:
    organization_id = uuid4()
    url = _build_restored_sqlite(tmp_path, [organization_id])
    guard = _LifecycleGuard(
        {
            organization_id: OrganizationLifecycleSnapshot(
                organization_id=organization_id,
                status="archived",
                work_allowed=False,
                updated_at=_EPISODE_AT,
                is_deleted=True,
                deleted_at=datetime(2026, 9, 1, tzinfo=UTC),
            )
        }
    )

    result = run_restore_organization_reconciliation(
        database_url=url,
        lifecycle_guard=guard,
    )

    assert result.ok is False
    assert result.deleted_count == 1
    assert "Core-deleted organizations" in (result.error_message or "")


class _UnavailableLifecycleGuard:
    def get_snapshot(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        raise OrganizationLifecycleUnavailableError(f"unavailable for {organization_id}")


def test_reconciliation_blocks_when_core_authority_is_unavailable(tmp_path: Path) -> None:
    organization_id = uuid4()
    url = _build_restored_sqlite(tmp_path, [organization_id])

    result = run_restore_organization_reconciliation(
        database_url=url,
        lifecycle_guard=_UnavailableLifecycleGuard(),
    )

    assert result.ok is False
    assert "authority could not establish current state" in (result.error_message or "")