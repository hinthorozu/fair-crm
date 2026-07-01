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


class CustomerSource(StrEnum):
    MANUAL = "manual"
    EXCEL = "excel"
    SCRAPER = "scraper"
