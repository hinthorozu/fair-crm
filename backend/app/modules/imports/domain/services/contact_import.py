"""Contact field resolution and duplicate matching for Excel import apply."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.contacts.domain.services.normalizers import normalize_email, normalize_phone
from app.shared.email import normalize_email_field

CONTACT_IMPORT_FIELD_KEYS = (
    "contact_first_name",
    "contact_last_name",
    "contact_title",
    "contact_department",
    "contact_email",
    "contact_phone",
    "contact_mobile_phone",
)

_PLACEHOLDER_LAST_NAME = "—"


def _is_nonempty(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def has_contact_import_fields(data: dict[str, Any]) -> bool:
    return any(_is_nonempty(data.get(key)) for key in CONTACT_IMPORT_FIELD_KEYS)


def resolve_contact_identity(data: dict[str, Any]) -> tuple[str, str]:
    """Derive first/last name from Yetkili import columns.

    Single-column Yetkili Adı is split on whitespace when possible; otherwise a
    placeholder last name is used so Contact entity validation still passes.
    Email-only rows fall back to the local-part of the address.
    """
    first_raw = str(data.get("contact_first_name") or "").strip()
    last_raw = str(data.get("contact_last_name") or "").strip()

    if first_raw and last_raw:
        return first_raw, last_raw

    if first_raw and not last_raw:
        parts = first_raw.split(None, 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return first_raw, _PLACEHOLDER_LAST_NAME

    if last_raw and not first_raw:
        parts = last_raw.split(None, 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return last_raw, _PLACEHOLDER_LAST_NAME

    email = data.get("contact_email")
    if _is_nonempty(email):
        local = str(email).split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
        if local:
            parts = local.split(None, 1)
            if len(parts) == 2:
                return parts[0].title(), parts[1].title()
            return local.title(), _PLACEHOLDER_LAST_NAME

    return "Yetkili", _PLACEHOLDER_LAST_NAME


def _normalize_contact_email(value: str | None) -> str | None:
    if not _is_nonempty(value):
        return None
    try:
        return normalize_email(value)
    except ValueError:
        return normalize_email_field(str(value).strip())


def _normalize_contact_phone(value: str | None) -> str | None:
    if not _is_nonempty(value):
        return None
    try:
        return normalize_phone(str(value))
    except ValueError:
        return str(value).strip()


def find_existing_contact_for_import(
    repository: ContactRepository,
    *,
    organization_id: UUID,
    customer_id: UUID,
    data: dict[str, Any],
) -> Contact | None:
    """Match existing contact by email, then phone, then name (in that order)."""
    email = _normalize_contact_email(data.get("contact_email"))
    if email is not None:
        found = repository.find_by_customer_and_email(organization_id, customer_id, email)
        if found is not None:
            return found

    for phone_key in ("contact_phone", "contact_mobile_phone"):
        phone = _normalize_contact_phone(data.get(phone_key))
        if phone is not None:
            found = repository.find_by_customer_and_phone(organization_id, customer_id, phone)
            if found is not None:
                return found

    first_name, last_name = resolve_contact_identity(data)
    if _is_nonempty(first_name) and _is_nonempty(last_name):
        return repository.find_by_customer_and_name(
            organization_id,
            customer_id,
            first_name.strip().lower(),
            last_name.strip().lower(),
        )
    return None
