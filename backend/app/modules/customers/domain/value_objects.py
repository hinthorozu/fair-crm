from enum import StrEnum


class CustomerType(StrEnum):
    EXHIBITOR = "exhibitor"
    VISITOR = "visitor"
    SUPPLIER = "supplier"
    SPONSOR = "sponsor"
    ORGANIZER = "organizer"
    PARTNER = "partner"
    LEAD = "lead"
    OTHER = "other"


class CustomerStatus(StrEnum):
    LEAD = "lead"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DELETED = "deleted"


class CustomerSource(StrEnum):
    MANUAL = "manual"
    EXCEL = "excel"
    SCRAPER = "scraper"


class CustomerMissingInfoFilter(StrEnum):
    """Server-side “Eksik Bilgiler” list/export filter values."""

    NO_WEBSITE = "no_website"
    NO_PHONE = "no_phone"
    NO_EMAIL = "no_email"
    NO_FAIR = "no_fair"
