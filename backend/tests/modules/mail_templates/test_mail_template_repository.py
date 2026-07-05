from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.mail_templates.domain.entities import MailTemplate
from app.modules.mail_templates.domain.exceptions import MailTemplateDefaultAlreadyExistsError
from app.modules.mail_templates.infrastructure.repositories.mail_template_repository import (
    SqlAlchemyMailTemplateRepository,
)


def test_mail_template_repository_crud(db_session, organization_id):
    repository = SqlAlchemyMailTemplateRepository(db_session)
    now = datetime.now(tz=UTC)
    template = MailTemplate.create(
        organization_id=organization_id,
        name="Welcome",
        key="welcome_email",
        subject="Hello",
        now=now,
    )
    saved = repository.add(template)
    assert saved.id == template.id

    fetched = repository.get_by_id(organization_id, saved.id)
    assert fetched is not None
    assert fetched.key == "welcome_email"

    by_key = repository.get_by_key(organization_id, "welcome_email")
    assert by_key is not None
    assert by_key.id == saved.id

    listed = repository.list_by_organization(organization_id)
    assert len(listed) == 1


def test_repository_maps_default_unique_violation_to_domain_error(db_session):
    repository = SqlAlchemyMailTemplateRepository(db_session)
    exc = IntegrityError(
        "UPDATE",
        {},
        Exception(
            "duplicate key value violates unique constraint "
            "uq_crm_mail_templates_org_type_lang_default"
        ),
    )

    with pytest.raises(MailTemplateDefaultAlreadyExistsError) as exc_info:
        repository._raise_integrity_error(exc)

    assert "varsayılan" in str(exc_info.value).lower()
