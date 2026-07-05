from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.domain.exceptions import (
    InvalidSmtpAccountEmailError,
    InvalidSmtpAccountNameError,
    InvalidSmtpAccountPortError,
    InvalidSmtpEncryptionTypeError,
)
from app.modules.smtp.domain.value_objects import SmtpEncryptionType


def test_smtp_account_create_with_defaults():
    now = datetime.now(tz=UTC)
    account = SmtpAccount.create(
        organization_id=uuid4(),
        name="Primary SMTP",
        from_email="noreply@example.com",
        host="smtp.example.com",
        port=587,
        now=now,
    )

    assert account.name == "Primary SMTP"
    assert account.from_email == "noreply@example.com"
    assert account.encryption_type == SmtpEncryptionType.STARTTLS
    assert account.is_default is False
    assert account.is_active is True
    assert account.deleted_at is None


def test_smtp_account_name_required():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidSmtpAccountNameError):
        SmtpAccount.create(
            organization_id=uuid4(),
            name="   ",
            from_email="noreply@example.com",
            host="smtp.example.com",
            port=587,
            now=now,
        )


def test_smtp_account_email_required():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidSmtpAccountEmailError):
        SmtpAccount.create(
            organization_id=uuid4(),
            name="Primary SMTP",
            from_email="invalid-email",
            host="smtp.example.com",
            port=587,
            now=now,
        )


def test_smtp_account_port_validation():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidSmtpAccountPortError):
        SmtpAccount.create(
            organization_id=uuid4(),
            name="Primary SMTP",
            from_email="noreply@example.com",
            host="smtp.example.com",
            port=70000,
            now=now,
        )


def test_smtp_account_encryption_type_validation():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidSmtpEncryptionTypeError):
        SmtpAccount.create(
            organization_id=uuid4(),
            name="Primary SMTP",
            from_email="noreply@example.com",
            host="smtp.example.com",
            port=587,
            encryption_type="invalid",
            now=now,
        )


def test_smtp_account_soft_delete_clears_default_and_active():
    now = datetime.now(tz=UTC)
    account = SmtpAccount.create(
        organization_id=uuid4(),
        name="Primary SMTP",
        from_email="noreply@example.com",
        host="smtp.example.com",
        port=587,
        is_default=True,
        now=now,
    )

    account.soft_delete(now=now)

    assert account.deleted_at == now
    assert account.is_default is False
    assert account.is_active is False
