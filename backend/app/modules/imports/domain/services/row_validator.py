import re
from typing import Any

from app.shared.email import normalize_email_field

_WEBSITE_PATTERN = re.compile(
    r"^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$",
    re.IGNORECASE,
)


def validate_import_row(normalized: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    company_name = normalized.get("company_name")
    if not company_name or not str(company_name).strip():
        errors.append("company_name is required")

    for field in ("email", "contact_email"):
        value = normalized.get(field)
        if not value:
            continue
        try:
            normalize_email_field(str(value))
        except ValueError as exc:
            errors.append(f"{field}: {exc}")

    website = normalized.get("website")
    if website:
        candidate = str(website).strip()
        if not candidate.startswith(("http://", "https://")):
            candidate = f"https://{candidate}"
        if not _WEBSITE_PATTERN.match(candidate):
            errors.append("website: invalid URL format")

    return errors
