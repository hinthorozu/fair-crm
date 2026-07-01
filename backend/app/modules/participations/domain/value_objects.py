from enum import StrEnum


class ParticipationStatus(StrEnum):
    PLANNED = "planned"
    EXHIBITOR = "exhibitor"
    VISITED = "visited"
    CONTACTED = "contacted"
    FOLLOW_UP_REQUIRED = "follow_up_required"
    NOT_INTERESTED = "not_interested"
    CUSTOMER = "customer"
    OTHER = "other"
