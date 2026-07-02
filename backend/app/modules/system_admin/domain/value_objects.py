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
