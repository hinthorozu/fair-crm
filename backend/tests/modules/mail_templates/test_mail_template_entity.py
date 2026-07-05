from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.mail_templates.domain.entities import MailTemplate
from app.modules.mail_templates.domain.exceptions import (
    InvalidMailTemplateKeyError,
    InvalidMailTemplateNameError,
    InvalidMailTemplateSubjectError,
)
from app.modules.mail_templates.domain.value_objects import MailTemplateType


def test_mail_template_create_with_defaults():
    now = datetime.now(tz=UTC)
    template = MailTemplate.create(
        organization_id=uuid4(),
        name="Welcome",
        key="welcome_email",
        subject="Hello",
        now=now,
    )
    assert template.template_type == MailTemplateType.TRANSACTIONAL
    assert template.language == "tr"
    assert template.is_active is True
    assert template.is_default is False


def test_mail_template_name_required():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidMailTemplateNameError):
        MailTemplate.create(
            organization_id=uuid4(),
            name="   ",
            key="welcome_email",
            subject="Hello",
            now=now,
        )


def test_mail_template_subject_required():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidMailTemplateSubjectError):
        MailTemplate.create(
            organization_id=uuid4(),
            name="Welcome",
            key="welcome_email",
            subject="   ",
            now=now,
        )


def test_mail_template_key_validation():
    now = datetime.now(tz=UTC)
    with pytest.raises(InvalidMailTemplateKeyError):
        MailTemplate.create(
            organization_id=uuid4(),
            name="Welcome",
            key="Invalid Key",
            subject="Hello",
            now=now,
        )


def test_mail_template_soft_delete_clears_default_and_active():
    now = datetime.now(tz=UTC)
    template = MailTemplate.create(
        organization_id=uuid4(),
        name="Welcome",
        key="welcome_email",
        subject="Hello",
        is_default=True,
        now=now,
    )
    template.soft_delete(now=now)
    assert template.deleted_at is not None
    assert template.is_active is False
    assert template.is_default is False
