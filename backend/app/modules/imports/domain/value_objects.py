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
    SHEET_SELECTED = "sheet_selected"
    HEADER_CONFIGURED = "header_configured"
    MAPPING_COMPLETED = "mapping_completed"
    ANALYSIS_QUEUED = "analysis_queued"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    ANALYSIS_FAILED = "analysis_failed"
    DECISION_REQUIRED = "decision_required"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # Legacy aliases — still accepted from DB / API during transition
    MAPPED = "mapped"
    PREVIEWED = "previewed"
    APPLIED = "applied"


class ImportSuggestedAction(StrEnum):
    CREATE_CUSTOMER_AND_PARTICIPATION = "create_customer_and_participation"
    LINK_EXISTING_CUSTOMER_TO_FAIR = "link_existing_customer_to_fair"
    UPDATE_PARTICIPATION = "update_participation"
    SKIP = "skip"


class ImportRowStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    READY_TO_CREATE = "ready_to_create"
    READY_TO_UPDATE = "ready_to_update"
    APPLIED = "applied"
    SKIPPED = "skipped"


class ExcelHeaderMode(StrEnum):
    FIRST_ROW_HEADER = "first_row_header"
    NO_HEADER = "no_header"
    MANUAL_HEADER_ROW = "manual_header_row"


class ImportJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ImportJobType(StrEnum):
    APPLY = "apply"
    ANALYZE = "analyze"
    BULK_DECISION = "bulk_decision"


class ImportDecision(StrEnum):
    CREATE_NEW = "create_new"
    UPDATE_EXISTING = "update_existing"
    PARTICIPATION_ONLY = "participation_only"
    SKIP = "skip"
    MANUAL_REVIEW = "manual_review"
