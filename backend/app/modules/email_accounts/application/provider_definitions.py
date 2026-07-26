"""Provider field / definition catalog used by API and dynamic UI forms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderFieldDefinition:
    key: str
    label: str
    field_type: str  # text | email | password
    required: bool = True
    secret: bool = False
    placeholder: str | None = None
    help_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "type": self.field_type,
            "required": self.required,
            "secret": self.secret,
            "placeholder": self.placeholder,
            "help_text": self.help_text,
        }


@dataclass(frozen=True)
class ProviderDefinition:
    provider_key: str
    display_name: str
    fields: tuple[ProviderFieldDefinition, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_key": self.provider_key,
            "display_name": self.display_name,
            "fields": [field.to_dict() for field in self.fields],
        }

    def secret_field_keys(self) -> frozenset[str]:
        return frozenset(field.key for field in self.fields if field.secret)

    def required_field_keys(self) -> frozenset[str]:
        return frozenset(field.key for field in self.fields if field.required)


MAILERSEND_PROVIDER_KEY = "mailersend"

MAILERSEND_DEFINITION = ProviderDefinition(
    provider_key=MAILERSEND_PROVIDER_KEY,
    display_name="MailerSend",
    fields=(
        ProviderFieldDefinition(
            key="api_token",
            label="API Token",
            field_type="password",
            required=True,
            secret=True,
            placeholder="MailerSend API token",
            help_text="Stored encrypted. Leave blank on edit to keep the current token.",
        ),
        ProviderFieldDefinition(
            key="from_email",
            label="Gönderen E-Mail",
            field_type="email",
            required=True,
            secret=False,
            placeholder="noreply@example.com",
        ),
        ProviderFieldDefinition(
            key="from_name",
            label="Gönderen Adı",
            field_type="text",
            required=True,
            secret=False,
            placeholder="FAIR CRM",
        ),
        ProviderFieldDefinition(
            key="webhook_signing_secret",
            label="Webhook Signing Secret",
            field_type="password",
            required=False,
            secret=True,
            placeholder="MailerSend webhook signing secret",
            help_text=(
                "MailerSend webhook Signing Secret. Stored encrypted. "
                "Leave blank on edit to keep the current secret."
            ),
        ),
    ),
)

_PROVIDER_DEFINITIONS: dict[str, ProviderDefinition] = {
    MAILERSEND_DEFINITION.provider_key: MAILERSEND_DEFINITION,
}


def list_provider_definitions() -> list[ProviderDefinition]:
    return list(_PROVIDER_DEFINITIONS.values())


def get_provider_definition(provider_key: str) -> ProviderDefinition | None:
    return _PROVIDER_DEFINITIONS.get((provider_key or "").strip().lower())


def require_provider_definition(provider_key: str) -> ProviderDefinition:
    definition = get_provider_definition(provider_key)
    if definition is None:
        raise ValueError(f"Unknown provider_key: {provider_key!r}")
    return definition
