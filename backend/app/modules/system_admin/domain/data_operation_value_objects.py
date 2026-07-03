from enum import StrEnum


class DataOperationRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DataOperationRunResult(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
