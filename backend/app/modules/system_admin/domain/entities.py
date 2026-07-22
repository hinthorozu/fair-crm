from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.system_admin.domain.value_objects import (
    RestoreJobSourceType,
    RestoreJobStatus,
    SystemBackupStage,
    SystemBackupStatus,
)
from app.shared.database_backup.database_keys import DatabaseKey
from app.shared.database_backup.formats import BackupFormat

@dataclass
class SystemBackup:
    id: UUID
    organization_id: UUID
    database_key: DatabaseKey
    file_name: str
    backup_format: BackupFormat
    file_size: Optional[int]
    status: SystemBackupStatus
    progress_stage: SystemBackupStage
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    created_by: UUID
    created_by_email: Optional[str]
    notes: Optional[str]
    checksum: Optional[str]
    manifest_json: dict | None
    download_count: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        database_key: DatabaseKey,
        file_name: str,
        backup_format: BackupFormat,
        created_by: UUID,
        created_by_email: str | None,
        notes: str | None,
        now: datetime,
    ) -> "SystemBackup":
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            database_key=database_key,
            file_name=file_name,
            backup_format=backup_format,
            file_size=None,
            status=SystemBackupStatus.RUNNING,
            progress_stage=SystemBackupStage.PREPARING,
            started_at=now,
            completed_at=None,
            duration_seconds=None,
            created_by=created_by,
            created_by_email=created_by_email,
            notes=notes,
            checksum=None,
            manifest_json=None,
            download_count=0,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def mark_stage(self, stage: SystemBackupStage, *, now: datetime) -> None:
        self.progress_stage = stage
        self.updated_at = now

    def mark_completed(
        self,
        *,
        file_size: int,
        checksum: str,
        duration_seconds: int,
        now: datetime,
        manifest_json: dict | None = None,
    ) -> None:
        self.status = SystemBackupStatus.COMPLETED
        self.progress_stage = SystemBackupStage.COMPLETED
        self.file_size = file_size
        self.checksum = checksum
        self.duration_seconds = duration_seconds
        self.completed_at = now
        self.updated_at = now
        self.error_message = None
        if manifest_json is not None:
            self.manifest_json = manifest_json

    def mark_failed(self, *, error_message: str, now: datetime) -> None:
        self.status = SystemBackupStatus.FAILED
        self.progress_stage = SystemBackupStage.FAILED
        self.error_message = error_message
        self.completed_at = now
        self.updated_at = now
        if self.started_at:
            self.duration_seconds = max(0, int((now - self.started_at).total_seconds()))

    def increment_download(self, *, now: datetime) -> None:
        self.download_count += 1
        self.updated_at = now


@dataclass
class SystemBackupRestoreJob:
    id: UUID
    organization_id: UUID
    source_type: RestoreJobSourceType
    source_database_key: DatabaseKey
    target_database_key: DatabaseKey
    backup_id: UUID | None
    uploaded_file_path: str | None
    source_file_name: str
    checksum_sha256: str | None
    status: RestoreJobStatus
    notes: str | None
    requested_by_user_id: UUID
    requested_by_email: str | None
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    restore_log_path: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        source_type: RestoreJobSourceType,
        source_database_key: DatabaseKey,
        target_database_key: DatabaseKey,
        backup_id: UUID | None,
        uploaded_file_path: str | None,
        source_file_name: str,
        checksum_sha256: str | None,
        notes: str | None,
        requested_by_user_id: UUID,
        requested_by_email: str | None,
        now: datetime,
    ) -> "SystemBackupRestoreJob":
        job_id = uuid4()
        return cls(
            id=job_id,
            organization_id=organization_id,
            source_type=source_type,
            source_database_key=source_database_key,
            target_database_key=target_database_key,
            backup_id=backup_id,
            uploaded_file_path=uploaded_file_path,
            source_file_name=source_file_name,
            checksum_sha256=checksum_sha256,
            status=RestoreJobStatus.MANUAL_RESTORE_REQUIRED,
            notes=notes,
            requested_by_user_id=requested_by_user_id,
            requested_by_email=requested_by_email,
            requested_at=now,
            started_at=None,
            completed_at=None,
            failed_at=None,
            error_message=None,
            restore_log_path=f"data/restore_logs/{job_id}.log",
            created_at=now,
            updated_at=now,
        )

    def mark_running(self, *, now: datetime, restore_log_path: str | None = None) -> None:
        self.status = RestoreJobStatus.RUNNING
        self.started_at = now
        self.updated_at = now
        if restore_log_path is not None:
            self.restore_log_path = restore_log_path

    def mark_completed(self, *, now: datetime) -> None:
        self.status = RestoreJobStatus.COMPLETED
        self.completed_at = now
        self.updated_at = now
        self.error_message = None

    def mark_failed(self, *, error_message: str, now: datetime) -> None:
        self.status = RestoreJobStatus.FAILED
        self.failed_at = now
        self.updated_at = now
        self.error_message = error_message
