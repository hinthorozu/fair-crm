from dataclasses import dataclass
from enum import StrEnum


class OperationType(StrEnum):
    SCRAPER = "scraper"
    EMAIL = "email"
    BULK_EMAIL = "bulk_email"
    ENRICHMENT = "enrichment"
    DUPLICATE_CHECK = "duplicate_check"
    DATA_CLEANUP = "data_cleanup"
    WHATSAPP = "whatsapp"
    MANUAL_TASK = "manual_task"
    REMINDER = "reminder"


class OperationStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunItemStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class SourceKind(StrEnum):
    FAIR = "fair"
    IMPORT = "import"
    SEGMENT = "segment"
    MANUAL_SELECTION = "manual_selection"
    CUSTOMER = "customer"
    NONE = "none"


class OperationPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ManualTaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class HandlerCapabilities:
    supports_pause: bool = False
    supports_resume: bool = False
    supports_retry: bool = False
    supports_schedule: bool = False
    supports_items: bool = False
