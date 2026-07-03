from __future__ import annotations

from app.modules.customers.application.commands import (
    CreateCustomerCommand,
    CustomerEmailInput,
    CustomerPhoneInput,
    CustomerWebsiteInput,
    UpdateCustomerCommand,
)
from app.modules.customers.application.communication_parsing import (
    CommunicationValueInput,
    emails_from_inputs,
    emails_from_scalar,
    phones_from_inputs,
    phones_from_scalar,
    websites_from_inputs,
    websites_from_scalar,
)


def _phone_inputs(items: list[CustomerPhoneInput] | None) -> list[CommunicationValueInput]:
    if not items:
        return []
    return [CommunicationValueInput(value=item.phone, is_primary=item.is_primary) for item in items]


def _email_inputs(items: list[CustomerEmailInput] | None) -> list[CommunicationValueInput]:
    if not items:
        return []
    return [CommunicationValueInput(value=item.email, is_primary=item.is_primary) for item in items]


def _website_inputs(items: list[CustomerWebsiteInput] | None) -> list[CommunicationValueInput]:
    if not items:
        return []
    return [CommunicationValueInput(value=item.website, is_primary=item.is_primary) for item in items]


def resolve_create_communications(
    command: CreateCustomerCommand,
) -> tuple[list[str], list[str], list[str]]:
    if command.phones is not None:
        phones = phones_from_inputs(_phone_inputs(command.phones))
    else:
        phones = phones_from_scalar(command.phone)

    if command.emails is not None:
        emails = emails_from_inputs(_email_inputs(command.emails))
    else:
        emails = emails_from_scalar(command.email)

    if command.websites is not None:
        websites = websites_from_inputs(_website_inputs(command.websites))
    else:
        websites = websites_from_scalar(command.website)

    return phones, emails, websites


def resolve_update_communications(
    command: UpdateCustomerCommand,
) -> tuple[list[str] | None, list[str] | None, list[str] | None, bool, bool, bool]:
    phones: list[str] | None = None
    emails: list[str] | None = None
    websites: list[str] | None = None
    sync_phone = False
    sync_email = False
    sync_website = False

    if "phones" in command.fields_set:
        phones = phones_from_inputs(_phone_inputs(command.phones))
        sync_phone = True
    elif "phone" in command.fields_set:
        phones = phones_from_scalar(command.phone)
        sync_phone = True

    if "emails" in command.fields_set:
        emails = emails_from_inputs(_email_inputs(command.emails))
        sync_email = True
    elif "email" in command.fields_set:
        emails = emails_from_scalar(command.email)
        sync_email = True

    if "websites" in command.fields_set:
        websites = websites_from_inputs(_website_inputs(command.websites))
        sync_website = True
    elif "website" in command.fields_set:
        websites = websites_from_scalar(command.website)
        sync_website = True

    return phones, emails, websites, sync_phone, sync_email, sync_website
