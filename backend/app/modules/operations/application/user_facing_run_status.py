"""Shared Operation Engine user-facing run status mapping.

Technical RunStatus values stay in the domain. This module only maps them to the
six user-facing states shown across all operation types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

# Canonical user-facing status keys (shared with frontend).
USER_FACING_SCHEDULED = "scheduled"
USER_FACING_RUNNING = "running"
USER_FACING_PAUSED = "paused"
USER_FACING_COMPLETED = "completed"
USER_FACING_CANCELLED = "cancelled"
USER_FACING_FAILED = "failed"

USER_FACING_STATUS_LABELS_TR: dict[str, str] = {
    USER_FACING_SCHEDULED: "Zamanlandı",
    USER_FACING_RUNNING: "Çalışıyor",
    USER_FACING_PAUSED: "Durduruldu",
    USER_FACING_COMPLETED: "Bitti",
    USER_FACING_CANCELLED: "İptal",
    USER_FACING_FAILED: "Hata",
}

USER_FACING_STATUSES = frozenset(USER_FACING_STATUS_LABELS_TR.keys())

# Technical run statuses that belong under each user-facing key (for list filters).
# NOTE: technical `queued` is NOT scheduled — it is immediate execution waiting on a worker.
USER_FACING_TO_TECHNICAL_RUN_STATUSES: dict[str, tuple[str, ...]] = {
    USER_FACING_SCHEDULED: ("scheduled",),
    USER_FACING_RUNNING: ("running", "queued"),
    USER_FACING_PAUSED: ("paused",),
    USER_FACING_COMPLETED: ("completed",),
    USER_FACING_CANCELLED: ("cancelled",),
    USER_FACING_FAILED: ("failed",),
}


def _parse_future_schedule(run_settings: Mapping[str, Any] | None) -> bool:
    """True only when run_settings encodes a real future schedule timestamp."""
    if not run_settings:
        return False
    raw = (
        run_settings.get("schedule")
        or run_settings.get("scheduled_at")
        or run_settings.get("run_at")
    )
    if not isinstance(raw, str) or not raw.strip():
        return False
    try:
        # Support trailing Z
        normalized = raw.strip().replace("Z", "+00:00")
        when = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when > datetime.now(timezone.utc)


def map_technical_run_status_to_user_facing(
    technical_status: str | None,
    *,
    run_settings: Mapping[str, Any] | None = None,
) -> str | None:
    """Map a technical OperationRun status to one of the six user-facing keys.

    - ``scheduled`` → Zamanlandı
    - ``running`` → Çalışıyor
    - ``paused`` → Durduruldu
    - ``completed`` → Bitti
    - ``cancelled`` → İptal
    - ``failed`` → Hata
    - ``queued`` → Çalışıyor, unless run_settings has a *future* schedule → Zamanlandı
    """
    if not technical_status:
        return None
    status = str(technical_status).strip().lower()
    if not status:
        return None

    if status == "scheduled":
        return USER_FACING_SCHEDULED
    if status == "queued":
        if _parse_future_schedule(run_settings):
            return USER_FACING_SCHEDULED
        # Immediate start waiting in the worker queue — not a future schedule.
        return USER_FACING_RUNNING
    if status == "running":
        return USER_FACING_RUNNING
    if status == "paused":
        return USER_FACING_PAUSED
    if status == "completed":
        return USER_FACING_COMPLETED
    if status == "cancelled":
        return USER_FACING_CANCELLED
    if status == "failed":
        return USER_FACING_FAILED
    return None


def expand_user_facing_status_filter(status: str | None) -> tuple[str, ...] | None:
    """Expand a user-facing (or technical) filter value to technical run statuses.

    Returns None when ``status`` is empty. Unknown values are returned as a
    single-item tuple so callers can still apply an exact match.
    """
    if status is None:
        return None
    key = str(status).strip().lower()
    if not key:
        return None
    if key in USER_FACING_TO_TECHNICAL_RUN_STATUSES:
        return USER_FACING_TO_TECHNICAL_RUN_STATUSES[key]
    return (key,)


def user_facing_status_label_tr(user_facing: str | None) -> str | None:
    if not user_facing:
        return None
    return USER_FACING_STATUS_LABELS_TR.get(user_facing)
