"""P0.1 tenant-isolation tests for email account/config repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)


def _create_smtp_account(repository, organization_id):
    now = datetime.now(tz=UTC)
    account = EmailAccount.create(
        organization_id=organization_id,
        name="Tenant SMTP",
        from_email="tenant@example.com",
        account_type=EmailAccountType.SMTP,
        is_default=True,
        now=now,
    )
    config = EmailAccountSmtpConfig.create(
        email_account_id=account.id,
        host="smtp.example.com",
        port=587,
        username="tenant-user",
        password="tenant-secret",
    )
    return repository.add_smtp_account(account, config)


def test_smtp_config_read_fails_closed_for_foreign_organization(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    repository = SqlAlchemyEmailAccountRepository(db_session)
    account, _ = _create_smtp_account(repository, owner_org)
    db_session.commit()

    assert repository.get_smtp_config(
        account.id,
        organization_id=foreign_org,
    ) is None

    owner_config = repository.get_smtp_config(
        account.id,
        organization_id=owner_org,
    )
    assert owner_config is not None
    assert owner_config.password == "tenant-secret"


def test_account_update_rejects_entity_with_foreign_organization(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    repository = SqlAlchemyEmailAccountRepository(db_session)
    account, _ = _create_smtp_account(repository, owner_org)
    db_session.commit()

    account.organization_id = foreign_org
    account.name = "Foreign overwrite"

    with pytest.raises(ValueError, match="Email account not found"):
        repository.update_account(account)

    db_session.expire_all()
    owner = repository.get_by_id(owner_org, account.id)
    assert owner is not None
    assert owner.organization_id == owner_org
    assert owner.name == "Tenant SMTP"


def test_smtp_account_update_rejects_entity_with_foreign_organization(db_session):
    owner_org = uuid4()
    foreign_org = uuid4()
    repository = SqlAlchemyEmailAccountRepository(db_session)
    account, config = _create_smtp_account(repository, owner_org)
    db_session.commit()

    account.organization_id = foreign_org
    account.name = "Foreign overwrite"
    config.host = "foreign.example.com"

    with pytest.raises(ValueError, match="Email account not found"):
        repository.update_smtp_account(account, config)

    db_session.expire_all()
    owner = repository.get_by_id(owner_org, account.id)
    owner_config = repository.get_smtp_config(
        account.id,
        organization_id=owner_org,
    )
    assert owner is not None
    assert owner.name == "Tenant SMTP"
    assert owner_config is not None
    assert owner_config.host == "smtp.example.com"
