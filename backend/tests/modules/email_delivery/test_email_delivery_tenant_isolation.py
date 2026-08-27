"""Tenant-isolation evidence for email-delivery side effects."""

from dataclasses import replace
from datetime import UTC, datetime

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.email_delivery.application.dispatcher import (
    deactivate_email_account_in_session,
)


def test_deactivate_helper_does_not_follow_foreign_organization_id(
    db_session,
    organization_id,
    other_organization_id,
):
    now = datetime.now(tz=UTC)
    account = EmailAccount.create(
        organization_id=organization_id,
        name="Owner SMTP",
        from_email="owner@example.com",
        now=now,
    )
    smtp_config = EmailAccountSmtpConfig.create(
        email_account_id=account.id,
        host="smtp.example.com",
        port=587,
        username="owner",
        password="secret",
    )
    repository = SqlAlchemyEmailAccountRepository(db_session)
    repository.add_smtp_account(account, smtp_config)

    foreign_pointer = replace(account, organization_id=other_organization_id)
    deactivate_email_account_in_session(db_session, foreign_pointer)

    owner_account = repository.get_by_id(organization_id, account.id)
    assert owner_account is not None
    assert owner_account.is_active is True
    assert repository.get_by_id(other_organization_id, account.id) is None
