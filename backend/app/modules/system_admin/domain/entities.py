from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.modules.system_admin.domain.value_objects import SystemBackupStage, SystemBackupStatus
from app.shared.database_backup.formats import BackupFormat


@dataclass
class SystemBackup:
    id: UUID
    organization_id: UUID
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
