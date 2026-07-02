from typing import Any

MIN_COMPANY_NAME_LENGTH = 2


def validate_import_row(normalized: dict[str, Any]) -> list[str]:
    """Validate a normalized import row using only Excel/mapping data (no CRM access).

    Sprint scope: company_name only — email, phone, website, etc. are not validated here.
    """
    errors: list[str] = []

    company_name = normalized.get("company_name")
    if not company_name or not str(company_name).strip():
        errors.append("no_company_name")
        return errors

    stripped = str(company_name).strip()
    if len(stripped) < MIN_COMPANY_NAME_LENGTH:
        errors.append("invalid_company_name")

    return errors
