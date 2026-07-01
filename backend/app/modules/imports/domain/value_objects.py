from enum import StrEnum


class ImportSourceType(StrEnum):
    """Import origin — only Excel is implemented in v1; others reserved for adapters."""

    EXCEL = "excel"
    PDF = "pdf"
    SCRAPER = "scraper"
    DATABASE = "database"
    MANUAL = "manual"
    OTHER = "other"


class ImportBatchStatus(StrEnum):
    UPLOADED = "uploaded"
    PREVIEWED = "previewed"
    APPLIED = "applied"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportRowStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    READY_TO_CREATE = "ready_to_create"
    READY_TO_UPDATE = "ready_to_update"
    APPLIED = "applied"
    SKIPPED = "skipped"


class ImportDecision(StrEnum):
    CREATE_NEW = "create_new"
    UPDATE_EXISTING = "update_existing"
    SKIP = "skip"
