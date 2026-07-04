"""Normalized exhibitor row for Import Engine handoff."""

from dataclasses import dataclass
from typing import Any

from app.modules.imports.domain.services.header_mapping import CANONICAL_FIELDS


@dataclass(frozen=True)
class NormalizedCompanyDto:
    """Canonical exhibitor fields aligned with the import pipeline."""

    company_name: str
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
    hall: str | None = None
    stand: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    linkedin_url: str | None = None
    youtube_url: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] | None = None

    def to_canonical_row(self) -> dict[str, str]:
        """Convert to import engine row dict (canonical field keys only)."""
        values = {
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone,
            "mobile_phone": self.mobile_phone,
            "website": self.website,
            "country": self.country,
            "city": self.city,
            "address": self.address,
            "tax_number": self.tax_number,
            "contact_first_name": self.contact_first_name,
            "contact_last_name": self.contact_last_name,
            "contact_title": self.contact_title,
            "contact_department": self.contact_department,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "contact_mobile_phone": self.contact_mobile_phone,
            "notes": self.notes,
            "hall": self.hall,
            "stand": self.stand,
            "instagram_url": self.instagram_url,
            "facebook_url": self.facebook_url,
            "linkedin_url": self.linkedin_url,
            "youtube_url": self.youtube_url,
        }
        row = {key: value for key, value in values.items() if value}
        unknown = set(row) - CANONICAL_FIELDS
        if unknown:
            raise ValueError(f"Normalized row contains non-canonical fields: {sorted(unknown)}")
        return row
