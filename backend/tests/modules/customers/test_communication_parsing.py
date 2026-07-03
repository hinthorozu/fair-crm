import pytest

from app.modules.customers.application.communication_parsing import (
    CommunicationValueInput,
    emails_from_inputs,
    phones_from_inputs,
)
from app.modules.customers.domain.exceptions import InvalidCustomerEmailError


def test_phones_from_inputs_moves_primary_first():
    values = phones_from_inputs(
        [
            CommunicationValueInput(value="0212 555 0101", is_primary=False),
            CommunicationValueInput(value="0532 555 0102", is_primary=True),
        ]
    )
    assert values == ["905325550102", "902125550101"]


def test_emails_from_inputs_rejects_invalid_email():
    with pytest.raises(InvalidCustomerEmailError):
        emails_from_inputs([CommunicationValueInput(value="not-an-email", is_primary=True)])
