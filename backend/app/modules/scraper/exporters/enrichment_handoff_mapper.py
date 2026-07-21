"""Map enrichment results to scraper raw company rows for import handoff."""

from __future__ import annotations

from app.modules.scraper.domain.enrichment_adapter import ENRICHMENT_REQUESTED_FIELD_KEYS
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto

_SOCIAL_METADATA_KEYS = {
    "instagram": "instagram_url",
    "facebook": "facebook_url",
    "linkedin": "linkedin_url",
    "youtube": "youtube_url",
}


def _first_value(items: list[SourcedValue]) -> str | None:
    return items[0].value if items else None


def _first_source(items: list[SourcedValue]) -> str | None:
    return items[0].source_url if items else None


def enrichment_result_to_raw_company(
    result: EnrichmentResultDto,
    *,
    requested_fields: list[str] | None = None,
) -> RawCompanyDto | None:
    """Convert a found enrichment result to a raw import row."""
    if result.status != "found":
        return None

    requested = {
        field
        for field in (requested_fields or ["email"])
        if field in ENRICHMENT_REQUESTED_FIELD_KEYS
    }

    metadata: dict[str, object] = {
        "external_id": str(result.customer_id),
        "customer_id": str(result.customer_id),
        "enrichment_status": result.status,
        "source_url": _first_source(result.emails) or _first_source(result.phones) or result.website,
    }
    if result.emails:
        metadata["email_source_url"] = result.emails[0].source_url
    if result.phones:
        metadata["phone_source_url"] = result.phones[0].source_url
    if result.address is not None:
        metadata["address_source_url"] = result.address.source_url

    extra_fields: dict[str, str] = {}

    # Pass every discovered address (semicolon-separated). Import apply merges with
    # existing CRM emails and drops duplicates — do not truncate to the first hit.
    email = (
        ";".join(item.value for item in result.emails)
        if "email" in requested and result.emails
        else None
    )
    phone = _first_value(result.phones) if "phone" in requested else None
    address = result.address.value if "address" in requested and result.address is not None else None

    for social_key, metadata_key in _SOCIAL_METADATA_KEYS.items():
        if social_key not in requested:
            continue
        sourced = result.social_links.get(social_key)
        if sourced is None:
            continue
        metadata[metadata_key] = sourced.value
        metadata[f"{social_key}_source_url"] = sourced.source_url

    return RawCompanyDto(
        company_name=result.company_name,
        source_url=str(metadata.get("source_url") or result.website),
        email=email,
        phone=phone,
        address=address,
        website=result.website,
        extra_fields=extra_fields,
        metadata=metadata,
    )


def enrichment_results_to_raw_companies(
    results: list[EnrichmentResultDto],
    *,
    requested_fields: list[str] | None = None,
) -> list[RawCompanyDto]:
    rows: list[RawCompanyDto] = []
    for result in results:
        raw = enrichment_result_to_raw_company(result, requested_fields=requested_fields)
        if raw is not None:
            rows.append(raw)
    return rows
