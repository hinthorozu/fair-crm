"""Recipient resolution unit tests."""

from uuid import uuid4

from app.modules.fair_emails.application.recipient_resolution import resolve_recipients
from app.modules.fair_emails.domain.value_objects import RawRecipientCandidate, RecipientOptions


def _candidate(**overrides):
    base = {
        "recipient_name": "ABC",
        "company_name": "ABC Fuarcılık",
        "email": "info@abc.com",
        "source": "customer",
        "customer_id": uuid4(),
        "contact_id": None,
        "participation_id": uuid4(),
        "is_active": True,
        "email_valid": True,
    }
    base.update(overrides)
    return RawRecipientCandidate(**base)


def test_resolve_recipients_dedupes_emails():
    customer_id = uuid4()
    result = resolve_recipients(
        [
            _candidate(customer_id=customer_id, email="info@abc.com", source="customer"),
            _candidate(
                customer_id=customer_id,
                email="info@abc.com",
                source="contact",
                contact_id=uuid4(),
            ),
        ],
        RecipientOptions(include_customer_emails=True, include_contact_emails=True, dedupe_emails=True),
    )
    will_send = [item for item in result.recipients if item.status == "will_send"]
    assert len(will_send) == 1
    assert result.skipped_count == 1


def test_resolve_recipients_excludes_inactive():
    result = resolve_recipients(
        [_candidate(is_active=False)],
        RecipientOptions(exclude_inactive=True),
    )
    assert result.recipients[0].status == "skip"
    assert result.recipients[0].skip_reason == "inactive_record"
