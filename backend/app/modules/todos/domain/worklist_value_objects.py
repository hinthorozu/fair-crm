from enum import StrEnum


class StoredWorklistPrimaryStatus(StrEnum):
    """Values persisted in crm_todo_worklist_states.primary_status."""

    IN_FOLLOW_UP = "in_follow_up"
    CLOSED = "closed"


class WorklistDisplayStatus(StrEnum):
    """API/computed worklist row status including virtual not_started."""

    NOT_STARTED = "not_started"
    IN_FOLLOW_UP = "in_follow_up"
    CLOSED = "closed"


class WorklistFilter(StrEnum):
    YAPILMADI = "yapilmadi"
    TAKIPTE = "takipte"
    KONU_KAPANDI = "konu_kapandi"
    HEPSI = "hepsi"


def resolve_worklist_display_status(
    stored_status: str | None,
) -> WorklistDisplayStatus:
    if stored_status is None:
        return WorklistDisplayStatus.NOT_STARTED
    return WorklistDisplayStatus(stored_status)
