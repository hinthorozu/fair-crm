"""Raw exhibitor row as extracted by a site-specific adapter."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawCompanyDto:
    """Unnormalized company record from a fair website."""

    company_name: str
    source_url: str | None = None
    hall: str | None = None
    stand: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile_phone: str | None = None
    website: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    tax_number: str | None = None
    contact_first_name: str | None = None
    contact_last_name: str | None = None
    contact_title: str | None = None
    contact_department: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_mobile_phone: str | None = None
    notes: str | None = None
    extra_fields: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
