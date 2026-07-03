"""Maps adapter output to canonical import fields."""

from app.modules.scraper.dto.normalized_company_dto import NormalizedCompanyDto
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


class CompanyNormalizer:
    """Normalizes ``RawCompanyDto`` records for Import Engine preview."""

    def normalize(self, raw: RawCompanyDto) -> NormalizedCompanyDto | None:
        company_name = _clean(raw.company_name)
        if not company_name:
            return None
        return NormalizedCompanyDto(
            company_name=company_name,
            email=_clean(raw.email),
            phone=_clean(raw.phone),
            mobile_phone=_clean(raw.mobile_phone),
            website=_clean(raw.website),
            country=_clean(raw.country),
            city=_clean(raw.city),
            address=_clean(raw.address),
            tax_number=_clean(raw.tax_number),
            contact_first_name=_clean(raw.contact_first_name),
            contact_last_name=_clean(raw.contact_last_name),
            contact_title=_clean(raw.contact_title),
            contact_department=_clean(raw.contact_department),
            contact_email=_clean(raw.contact_email),
            contact_phone=_clean(raw.contact_phone),
            contact_mobile_phone=_clean(raw.contact_mobile_phone),
            notes=_clean(raw.notes),
            hall=_clean(raw.hall),
            stand=_clean(raw.stand),
            source_url=_clean(raw.source_url),
            metadata=dict(raw.metadata) if raw.metadata else None,
        )

    def normalize_many(self, rows: list[RawCompanyDto]) -> tuple[list[NormalizedCompanyDto], list[str]]:
        normalized: list[NormalizedCompanyDto] = []
        warnings: list[str] = []
        for index, raw in enumerate(rows):
            item = self.normalize(raw)
            if item is None:
                warnings.append(f"Row {index + 1}: skipped — empty company_name")
                continue
            normalized.append(item)
        return normalized, warnings
