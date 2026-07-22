from enum import StrEnum


class ActivityType(StrEnum):
    CALL = "call"
    MEETING = "meeting"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    NOTE = "note"
    FAIR_VISIT = "fair_visit"
    FOLLOW_UP = "follow_up"
    TASK_COMPLETED = "task_completed"
    OTHER = "other"


class ActivityStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ActivitySource(StrEnum):
    MANUAL = "manual"
    SYSTEM = "system"
    EMAIL_AUTOMATION = "email_automation"
    WHATSAPP_INTEGRATION = "whatsapp_integration"
    IMPORT = "import"
    OTHER = "other"
