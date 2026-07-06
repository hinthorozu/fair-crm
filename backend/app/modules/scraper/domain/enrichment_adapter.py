"""Constants and helpers for the customer contact enrichment adapter."""

from __future__ import annotations

from app.modules.scraper.types.scraper_site import ScraperSiteKey

CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY = ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT

ENRICHMENT_REQUESTED_FIELD_KEYS: frozenset[str] = frozenset(
    {"email", "phone", "address", "instagram", "facebook", "linkedin", "youtube"}
)

DEFAULT_ENRICHMENT_REQUESTED_FIELDS: tuple[str, ...] = ("email",)

MATCH_REASON_ENRICHMENT_CUSTOMER_ID = "enrichment_customer_id"


def is_customer_contact_enrichment_adapter(adapter_key: str | None) -> bool:
    return (adapter_key or "").strip().lower() == CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY
