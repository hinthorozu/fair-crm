from typing import Any

from app.modules.imports.domain.services.company_name_normalizer import normalize_import_company_name


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def normalize_row_data(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw import row into canonical field dict."""
    company_name = _clean_str(raw.get("company_name"))
    normalized: dict[str, Any] = {
        "company_name": company_name,
        "normalized_company_name": normalize_import_company_name(company_name or ""),
        "email": _clean_str(raw.get("email")),
        "phone": _clean_str(raw.get("phone")),
        "mobile_phone": _clean_str(raw.get("mobile_phone")),
        "website": _clean_str(raw.get("website")),
        "country": _clean_str(raw.get("country")),
        "city": _clean_str(raw.get("city")),
        "address": _clean_str(raw.get("address")),
        "tax_number": _clean_str(raw.get("tax_number")),
        "contact_first_name": _clean_str(raw.get("contact_first_name")),
        "contact_last_name": _clean_str(raw.get("contact_last_name")),
        "contact_title": _clean_str(raw.get("contact_title")),
        "contact_department": _clean_str(raw.get("contact_department")),
        "contact_email": _clean_str(raw.get("contact_email")),
        "contact_phone": _clean_str(raw.get("contact_phone")),
        "contact_mobile_phone": _clean_str(raw.get("contact_mobile_phone")),
        "notes": _clean_str(raw.get("notes")),
        "fair_name": _clean_str(raw.get("fair_name")),
        "hall": _clean_str(raw.get("hall")),
        "stand": _clean_str(raw.get("stand")),
    }
    return normalized
