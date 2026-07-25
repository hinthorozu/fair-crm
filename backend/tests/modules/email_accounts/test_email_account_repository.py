"""Email account repository + org-wide default regression."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.email_accounts.domain.entities import EmailAccount, EmailAccountSmtpConfig
from app.modules.email_accounts.domain.value_objects import EmailAccountType
from app.modules.email_accounts.infrastructure.persistence.mappers import account_entity_to_model
from app.modules.email_accounts.infrastructure.repositories.email_account_repository import (
    SqlAlchemyEmailAccountRepository,
)
from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import (
    SqlAlchemySmtpAccountRepository,
)


def test_smtp_repository_roundtrip_preserves_id_and_credentials(db_session):
    organization_id = uuid4()
    smtp_repo = SqlAlchemySmtpAccountRepository(db_session)
    now = datetime.now(tz=UTC)

    created = smtp_repo.add(
        SmtpAccount.create(
            organization_id=organization_id,
            name="Primary",
            from_email="noreply@example.com",
            host="smtp.example.com",
            port=587,
            username="user",
            password="secret",
            is_default=True,
            now=now,
        )
    )
    db_session.flush()

    loaded = smtp_repo.get_by_id(organization_id, created.id)
    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.host == "smtp.example.com"
    assert loaded.password == "secret"
    assert loaded.is_default is True

    email_repo = SqlAlchemyEmailAccountRepository(db_session)
    account = email_repo.get_by_id(organization_id, created.id)
    assert account is not None
    assert account.account_type == EmailAccountType.SMTP
    assert account.provider_key is None
    config = email_repo.get_smtp_config(created.id)
    assert config is not None
    assert config.password == "secret"


def test_organization_wide_single_default_across_account_types(db_session):
    organization_id = uuid4()
    email_repo = SqlAlchemyEmailAccountRepository(db_session)
    now = datetime.now(tz=UTC)

    smtp_account = EmailAccount.create(
        organization_id=organization_id,
        name="SMTP A",
        from_email="smtp@example.com",
        account_type=EmailAccountType.SMTP,
        is_default=True,
        now=now,
    )
    smtp_config = EmailAccountSmtpConfig.create(
        email_account_id=smtp_account.id,
        host="smtp.example.com",
        port=587,
        password="secret",
    )
    email_repo.add_smtp_account(smtp_account, smtp_config)

    provider = EmailAccount.create(
        organization_id=organization_id,
        name="Provider B",
        from_email="provider@example.com",
        account_type=EmailAccountType.PROVIDER,
        provider_key="fake",
        is_default=False,
        now=now,
    )
    email_repo.clear_default_for_organization(organization_id)
    email_repo.flush()
    provider.mark_as_default(now=now)
    db_session.add(account_entity_to_model(provider))
    db_session.flush()

    default = email_repo.get_default_for_organization(organization_id)
    assert default is not None
    assert default.id == provider.id
    assert default.account_type == EmailAccountType.PROVIDER

    smtp_again = email_repo.get_by_id(organization_id, smtp_account.id)
    assert smtp_again is not None
    assert smtp_again.is_default is False
