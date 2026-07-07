from enum import StrEnum


class SystemBackupStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SystemBackupStage(StrEnum):
    PREPARING = "preparing"
    DUMPING = "dumping"
    COMPRESSING = "compressing"
    COMPLETED = "completed"
    FAILED = "failed"


class RestoreJobSourceType(StrEnum):
    EXISTING_BACKUP = "existing_backup"
    UPLOADED_FILE = "uploaded_file"


class RestoreJobStatus(StrEnum):
    MANUAL_RESTORE_REQUIRED = "manual_restore_required"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
