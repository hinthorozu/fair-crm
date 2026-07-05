from datetime import UTC, datetime
from uuid import uuid4

from app.modules.smtp.domain.entities import SmtpAccount
from app.modules.smtp.infrastructure.repositories.smtp_account_repository import (
    SqlAlchemySmtpAccountRepository,
)


def _create_account(
    organization_id,
    *,
    name: str,
    is_default: bool = False,
) -> SmtpAccount:
    now = datetime.now(tz=UTC)
    return SmtpAccount.create(
        organization_id=organization_id,
        name=name,
        from_email=f"{name.lower().replace(' ', '-')}@example.com",
        host="smtp.example.com",
        port=587,
        is_default=is_default,
        now=now,
    )


def test_repository_clear_default_for_organization(db_session):
    organization_id = uuid4()
    repository = SqlAlchemySmtpAccountRepository(db_session)
    now = datetime.now(tz=UTC)

    first = repository.add(_create_account(organization_id, name="First", is_default=True))
    second = repository.add(_create_account(organization_id, name="Second", is_default=False))

    repository.clear_default_for_organization(organization_id, exclude_account_id=second.id)
    second.mark_as_default(now=now)
    repository.update(second)
    db_session.flush()

    refreshed_first = repository.get_by_id(organization_id, first.id)
    refreshed_second = repository.get_by_id(organization_id, second.id)

    assert refreshed_first is not None
    assert refreshed_second is not None
    assert refreshed_first.is_default is False
    assert refreshed_second.is_default is True


def test_repository_only_one_default_per_organization(db_session):
    organization_id = uuid4()
    other_org_id = uuid4()
    repository = SqlAlchemySmtpAccountRepository(db_session)
    now = datetime.now(tz=UTC)

    first = repository.add(_create_account(organization_id, name="Primary", is_default=True))
    second = repository.add(_create_account(organization_id, name="Backup", is_default=False))
    other_org = repository.add(_create_account(other_org_id, name="Other Org", is_default=True))

    repository.clear_default_for_organization(organization_id, exclude_account_id=second.id)
    second.mark_as_default(now=now)
    repository.update(second)
    db_session.flush()

    defaults = [
        account
        for account in repository.list_by_organization(organization_id)
        if account.is_default
    ]

    assert len(defaults) == 1
    assert defaults[0].id == second.id
    assert repository.get_default_for_organization(organization_id).id == second.id
    assert repository.get_by_id(organization_id, first.id).is_default is False
    assert repository.get_default_for_organization(other_org_id).id == other_org.id
