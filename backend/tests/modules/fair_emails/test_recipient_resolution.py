"""Recipient resolution unit tests."""

from uuid import uuid4

import pytest

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
    assert result.duplicate_count == 1
    assert result.invalid_count == 0


def test_resolve_recipients_skips_invalid_email_before_dedupe():
    customer_id = uuid4()
    result = resolve_recipients(
        [
            _candidate(customer_id=customer_id, email="valid@example.com", email_valid=True),
            _candidate(
                customer_id=customer_id,
                email="bad-email",
                email_valid=True,  # loader flag must not override shared validator
            ),
            _candidate(
                customer_id=customer_id,
                email="second@example.com",
                email_valid=True,
                contact_id=uuid4(),
                source="contact",
            ),
        ],
        RecipientOptions(),
    )
    will_send = [item for item in result.recipients if item.status == "will_send"]
    skipped = [item for item in result.recipients if item.status == "skip"]
    assert len(will_send) == 2
    assert {item.email for item in will_send} == {"valid@example.com", "second@example.com"}
    assert len(skipped) == 1
    assert skipped[0].skip_reason == "invalid_email"
    assert result.invalid_count == 1
    assert result.valid_email_count == 2
    assert result.deduped_recipient_count == 2


def test_resolve_recipients_whitespace_email_normalized():
    result = resolve_recipients(
        [_candidate(email="  Valid@Example.com  ", email_valid=True)],
        RecipientOptions(),
    )
    assert result.recipients[0].status == "will_send"
    assert result.recipients[0].email == "valid@example.com"


def test_resolve_recipients_invalid_not_counted_as_duplicate():
    customer_id = uuid4()
    result = resolve_recipients(
        [
            _candidate(customer_id=customer_id, email="one@example.com"),
            _candidate(customer_id=customer_id, email="not-an-email", email_valid=False),
            _candidate(customer_id=customer_id, email="two@example.com", contact_id=uuid4(), source="contact"),
            _candidate(customer_id=customer_id, email="one@example.com", contact_id=uuid4(), source="contact"),
        ],
        RecipientOptions(),
    )
    assert result.valid_email_count == 2
    assert result.invalid_count == 1
    assert result.duplicate_count == 1
    assert result.deduped_recipient_count == 2


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
    assert result.customer_consent_skipped_count == 2
    assert result.contact_consent_skipped_count == 0
    assert result.deduped_recipient_count == 0
    assert result.skipped_count == 2


def test_resolve_recipients_consent_claims_email_once_most_restrictive():
    customer_id = uuid4()
    result = resolve_recipients(
        [
            _candidate(
                customer_id=customer_id,
                source="customer",
                email="shared@abc.com",
                customer_email_allowed=True,
            ),
            _candidate(
                customer_id=customer_id,
                source="contact",
                contact_id=uuid4(),
                email="shared@abc.com",
                customer_email_allowed=True,
                contact_email_allowed=False,
            ),
        ],
        RecipientOptions(),
    )
    # Contact denial applies to the shared address for every candidate.
    assert result.contact_consent_skipped_count == 1
    assert result.duplicate_count == 1
    assert result.deduped_recipient_count == 0
    assert result.recipients[0].status == "skip"
    assert result.recipients[0].skip_reason == "contact_email_consent"
    assert result.recipients[1].skip_reason == "duplicate_email"


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
    assert result.contact_consent_skipped_count == 1
    assert result.customer_consent_skipped_count == 0
    assert result.deduped_recipient_count == 1


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Üinfo@example.com", "uinfo@example.com"),
        ("Şinfo@example.com", "sinfo@example.com"),
        ("Ğinfo@example.com", "ginfo@example.com"),
        ("Çinfo@example.com", "cinfo@example.com"),
        ("Öinfo@example.com", "oinfo@example.com"),
        ("Iinfo@example.com", "iinfo@example.com"),
        ("BİLGİ@EXAMPLE.COM", "bilgi@example.com"),
    ],
)
def test_resolve_fair_company_email_turkish_char_normalization(raw: str, expected: str):
    result = resolve_recipients(
        [_candidate(email=raw, source="customer")],
        RecipientOptions(),
    )
    assert result.recipients[0].status == "will_send"
    assert result.recipients[0].email == expected
    assert result.recipients[0].source == "customer"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Üinfo@example.com", "uinfo@example.com"),
        ("Şinfo@example.com", "sinfo@example.com"),
        ("Ğinfo@example.com", "ginfo@example.com"),
        ("Çinfo@example.com", "cinfo@example.com"),
        ("Öinfo@example.com", "oinfo@example.com"),
        ("Iinfo@example.com", "iinfo@example.com"),
        ("BİLGİ@EXAMPLE.COM", "bilgi@example.com"),
    ],
)
def test_resolve_fair_contact_email_turkish_char_normalization(raw: str, expected: str):
    result = resolve_recipients(
        [
            _candidate(
                email=raw,
                source="contact",
                contact_id=uuid4(),
                recipient_name="Yetkili",
            )
        ],
        RecipientOptions(),
    )
    assert result.recipients[0].status == "will_send"
    assert result.recipients[0].email == expected
    assert result.recipients[0].source == "contact"


def test_resolve_fair_emails_dedupe_after_turkish_normalization():
    customer_id = uuid4()
    result = resolve_recipients(
        [
            _candidate(customer_id=customer_id, email="Üinfo@example.com", source="customer"),
            _candidate(
                customer_id=customer_id,
                email="uinfo@example.com",
                source="contact",
                contact_id=uuid4(),
            ),
        ],
        RecipientOptions(dedupe_emails=True),
    )
    will_send = [item for item in result.recipients if item.status == "will_send"]
    skipped = [item for item in result.recipients if item.status == "skip"]
    assert len(will_send) == 1
    assert will_send[0].email == "uinfo@example.com"
    assert len(skipped) == 1
    assert skipped[0].skip_reason == "duplicate_email"
    assert result.duplicate_count == 1
