from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from app.modules.customers.domain.communication_entities import CustomerCommunications
from app.modules.customers.domain.exceptions import InvalidCustomerEmailError
from app.modules.customers.domain.services.normalizers import (
    normalize_email,
    normalize_phone,
    normalize_website,
)
from app.shared.email import is_valid_email_address, normalize_email_field

T = TypeVar("T")


@dataclass(frozen=True)
class CommunicationValueInput:
    value: str
    is_primary: bool = False


def phones_from_scalar(phone: Optional[str]) -> list[str]:
    if not phone:
        return []
    normalized = normalize_phone(phone)
    return [normalized] if normalized else []


def emails_from_scalar(email: Optional[str]) -> list[str]:
    if not email:
        return []
    try:
        normalized = normalize_email_field(email)
    except ValueError as exc:
        raise InvalidCustomerEmailError(str(exc)) from exc
    if not normalized:
        return []
    return normalized.split(";")


def websites_from_scalar(website: Optional[str]) -> list[str]:
    if not website:
        return []
    normalized = normalize_website(website)
    return [normalized] if normalized else []


def _ordered_values_with_primary(
    items: list[CommunicationValueInput],
    normalize_fn: Callable[[str], str],
) -> list[str]:
    normalized_items: list[tuple[str, bool]] = []
    seen: set[str] = set()

    for item in items:
        raw = item.value.strip()
        if not raw:
            continue
        value = normalize_fn(raw)
        if not value or value in seen:
            continue
        seen.add(value)
        normalized_items.append((value, item.is_primary))

    if not normalized_items:
        return []

    primary_index = next((index for index, (_, is_primary) in enumerate(normalized_items) if is_primary), 0)
    if primary_index != 0:
        primary_item = normalized_items.pop(primary_index)
        normalized_items.insert(0, primary_item)

    return [value for value, _ in normalized_items]


def phones_from_inputs(items: list[CommunicationValueInput]) -> list[str]:
    return _ordered_values_with_primary(items, normalize_phone)


def emails_from_inputs(items: list[CommunicationValueInput]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    primary_index: int | None = None

    for index, item in enumerate(items):
        raw = item.value.strip()
        if not raw:
            continue
        email = normalize_email(raw)
        if not is_valid_email_address(email):
            raise InvalidCustomerEmailError(f"Invalid email address: {raw}")
        if email in seen:
            continue
        seen.add(email)
        if item.is_primary and primary_index is None:
            primary_index = len(ordered)
        ordered.append(email)

    if not ordered:
        return []

    chosen_primary = primary_index if primary_index is not None else 0
    if chosen_primary != 0:
        primary_value = ordered.pop(chosen_primary)
        ordered.insert(0, primary_value)

    return ordered


def websites_from_inputs(items: list[CommunicationValueInput]) -> list[str]:
    return _ordered_values_with_primary(items, normalize_website)


def denormalized_phone(phones: list[str]) -> Optional[str]:
    return phones[0] if phones else None


def denormalized_email(emails: list[str]) -> Optional[str]:
    if not emails:
        return None
    return ";".join(emails)


def denormalized_website(websites: list[str]) -> Optional[str]:
    return websites[0] if websites else None


def api_scalar_fields_from_communications(
    communications: CustomerCommunications | None,
) -> tuple[Optional[str], Optional[str], Optional[str], int, int, int]:
    if communications is None:
        return None, None, None, 0, 0, 0

    phone_values = [item.phone for item in communications.phones]
    email_values = [item.email for item in communications.emails]
    website_values = [item.website for item in communications.websites]

    return (
        denormalized_phone(phone_values),
        denormalized_email(email_values),
        denormalized_website(website_values),
        max(len(phone_values) - 1, 0),
        max(len(email_values) - 1, 0),
        max(len(website_values) - 1, 0),
    )
