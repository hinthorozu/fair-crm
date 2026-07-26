"""Provider definition catalog tests."""

from app.modules.email_accounts.application.provider_definitions import (
    get_provider_definition,
    list_provider_definitions,
)


def test_mailersend_definition_has_required_secret_fields():
    definitions = list_provider_definitions()
    assert any(item.provider_key == "mailersend" for item in definitions)
    mailersend = get_provider_definition("mailersend")
    assert mailersend is not None
    assert mailersend.display_name == "MailerSend"
    fields = {field.key: field for field in mailersend.fields}
    assert fields["api_token"].secret is True
    assert fields["api_token"].required is True
    assert fields["api_token"].field_type == "password"
    assert fields["from_email"].field_type == "email"
    assert fields["from_name"].required is True
