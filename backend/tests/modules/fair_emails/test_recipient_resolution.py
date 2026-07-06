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


def test_resolve_recipients_customer_email_consent_blocks_all():
    customer_id = uuid4()
    result = resolve_recipients(
        [
            _candidate(
                customer_id=customer_id,
                source="customer",
                email="info@abc.com",
                customer_email_allowed=False,
            ),
            _candidate(
                customer_id=customer_id,
                source="contact",
                contact_id=uuid4(),
                email="contact@abc.com",
                customer_email_allowed=False,
                contact_email_allowed=True,
            ),
        ],
        RecipientOptions(),
    )
    assert all(item.status == "skip" for item in result.recipients)
    assert result.recipients[0].skip_reason == "customer_email_consent"
    assert result.recipients[1].skip_reason == "customer_email_consent"


def test_resolve_recipients_contact_email_consent_blocks_contact_only():
    customer_id = uuid4()
    result = resolve_recipients(
        [
            _candidate(customer_id=customer_id, source="customer", email="info@abc.com"),
            _candidate(
                customer_id=customer_id,
                source="contact",
                contact_id=uuid4(),
                email="blocked@abc.com",
                contact_email_allowed=False,
            ),
        ],
        RecipientOptions(),
    )
    will_send = [item for item in result.recipients if item.status == "will_send"]
    skipped = [item for item in result.recipients if item.status == "skip"]
    assert len(will_send) == 1
    assert will_send[0].source == "customer"
    assert len(skipped) == 1
    assert skipped[0].skip_reason == "contact_email_consent"
