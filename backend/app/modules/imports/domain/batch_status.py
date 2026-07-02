"""Import batch status helpers — lifecycle transitions and legacy aliases."""

from app.modules.imports.domain.value_objects import ImportBatchStatus

# Legacy DB values normalized on read/write paths
_LEGACY_STATUS_ALIASES: dict[str, ImportBatchStatus] = {
    "mapped": ImportBatchStatus.MAPPING_COMPLETED,
    "applied": ImportBatchStatus.COMPLETED,
}

# Sprint grid mapping dropdown fields (company_name only required for analyze)
GRID_MAPPING_FIELDS: frozenset[str] = frozenset(
    {
        "company_name",
        "phone",
        "email",
        "website",
        "contact_first_name",
        "country",
        "city",
        "address",
        "stand",
        "hall",
        "notes",
    }
)

TERMINAL_BATCH_STATUSES: frozenset[ImportBatchStatus] = frozenset(
    {
        ImportBatchStatus.COMPLETED,
        ImportBatchStatus.FAILED,
        ImportBatchStatus.CANCELLED,
        ImportBatchStatus.APPLIED,  # legacy
    }
)

ACTIVE_ANALYZE_BATCH_STATUSES: frozenset[ImportBatchStatus] = frozenset(
    {
        ImportBatchStatus.ANALYSIS_QUEUED,
        ImportBatchStatus.ANALYZING,
    }
)


def normalize_batch_status(value: str | ImportBatchStatus) -> ImportBatchStatus:
    if isinstance(value, ImportBatchStatus):
        return value
    if value in _LEGACY_STATUS_ALIASES:
        return _LEGACY_STATUS_ALIASES[value]
    return ImportBatchStatus(value)


def is_batch_terminal(status: ImportBatchStatus | str) -> bool:
    return normalize_batch_status(status) in TERMINAL_BATCH_STATUSES


def can_start_analyze(status: ImportBatchStatus | str) -> bool:
    normalized = normalize_batch_status(status)
    return normalized in (
        ImportBatchStatus.MAPPING_COMPLETED,
        ImportBatchStatus.ANALYSIS_FAILED,
    )


def can_open_decisions(status: ImportBatchStatus | str) -> bool:
    normalized = normalize_batch_status(status)
    return normalized in (
        ImportBatchStatus.ANALYZED,
        ImportBatchStatus.DECISION_REQUIRED,
        ImportBatchStatus.APPLYING,
    )


SETUP_RESUME_STATUSES: frozenset[ImportBatchStatus] = frozenset(
    {
        ImportBatchStatus.UPLOADED,
        ImportBatchStatus.SHEET_SELECTED,
        ImportBatchStatus.HEADER_CONFIGURED,
    }
)


def can_resume_setup(status: ImportBatchStatus | str) -> bool:
    return normalize_batch_status(status) in SETUP_RESUME_STATUSES


ACTIVE_BATCH_OPERATION_STATUSES: frozenset[ImportBatchStatus] = frozenset(
    {
        ImportBatchStatus.ANALYSIS_QUEUED,
        ImportBatchStatus.ANALYZING,
        ImportBatchStatus.APPLYING,
    }
)


def has_active_batch_operation(status: ImportBatchStatus | str) -> bool:
    return normalize_batch_status(status) in ACTIVE_BATCH_OPERATION_STATUSES


def resume_setup_step_id(status: ImportBatchStatus | str) -> str | None:
    """Wizard setup step id for resume (fair/upload excluded — job already created)."""
    normalized = normalize_batch_status(status)
    return {
        ImportBatchStatus.UPLOADED: "sheet",
        ImportBatchStatus.SHEET_SELECTED: "header",
        ImportBatchStatus.HEADER_CONFIGURED: "mapping",
    }.get(normalized)
