"""Mail template aggregate — tenant-scoped reusable email content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from app.modules.mail_templates.domain.exceptions import (
    InvalidMailTemplateKeyError,
    InvalidMailTemplateLanguageError,
    InvalidMailTemplateNameError,
    InvalidMailTemplateSubjectError,
    InvalidMailTemplateTypeError,
    MailTemplateAlreadyDeletedError,
    MailTemplateNotDefaultEligibleError,
)
from app.modules.mail_templates.domain.value_objects import MailTemplateType

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")


def _normalize_template_type(value: str | MailTemplateType) -> MailTemplateType:
    if isinstance(value, MailTemplateType):
        return value
    normalized = value.strip().lower()
    try:
        return MailTemplateType(normalized)
    except ValueError as exc:
        raise InvalidMailTemplateTypeError(
            f"template_type must be one of: {', '.join(item.value for item in MailTemplateType)}"
        ) from exc


def _validate_key(key: str) -> str:
    normalized = key.strip().lower()
    if not normalized or not _KEY_PATTERN.match(normalized):
        raise InvalidMailTemplateKeyError(
            "key must start with a letter and contain only lowercase letters, digits, and underscores"
        )
    return normalized


def _validate_language(language: str) -> str:
    normalized = language.strip()
    if not normalized or not _LANGUAGE_PATTERN.match(normalized):
        raise InvalidMailTemplateLanguageError("language must be a valid locale code such as tr or en-US")
    return normalized


@dataclass
class MailTemplate:
    id: UUID
    organization_id: UUID
    name: str
    key: str
    subject: str
    body_html: Optional[str]
    body_text: Optional[str]
    template_type: MailTemplateType
    language: str
    is_active: bool
    is_default: bool
    variables_schema: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        name: str,
        key: str,
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        template_type: str | MailTemplateType = MailTemplateType.TRANSACTIONAL,
        language: str = "tr",
        is_active: bool = True,
        is_default: bool = False,
        variables_schema: Optional[dict[str, Any]] = None,
        now: datetime,
    ) -> MailTemplate:
        trimmed_name = name.strip()
        if not trimmed_name:
            raise InvalidMailTemplateNameError("name must not be empty")

        trimmed_subject = subject.strip()
        if not trimmed_subject:
            raise InvalidMailTemplateSubjectError("subject must not be empty")

        return cls(
            id=uuid4(),
            organization_id=organization_id,
            name=trimmed_name,
            key=_validate_key(key),
            subject=trimmed_subject,
            body_html=body_html,
            body_text=body_text,
            template_type=_normalize_template_type(template_type),
            language=_validate_language(language),
            is_active=is_active,
            is_default=is_default,
            variables_schema=variables_schema,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    def ensure_mutable(self) -> None:
        if self.deleted_at is not None:
            raise MailTemplateAlreadyDeletedError("Mail template is deleted")

    def update_fields(
        self,
        *,
        name: Optional[str] = None,
        key: Optional[str] = None,
        subject: Optional[str] = None,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        template_type: str | MailTemplateType | None = None,
        language: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None,
        variables_schema: Optional[dict[str, Any]] = None,
        now: datetime,
    ) -> None:
        self.ensure_mutable()

        if name is not None:
            trimmed = name.strip()
            if not trimmed:
                raise InvalidMailTemplateNameError("name must not be empty")
            self.name = trimmed

        if key is not None:
            self.key = _validate_key(key)

        if subject is not None:
            trimmed = subject.strip()
            if not trimmed:
                raise InvalidMailTemplateSubjectError("subject must not be empty")
            self.subject = trimmed

        if body_html is not None:
            self.body_html = body_html

        if body_text is not None:
            self.body_text = body_text

        if template_type is not None:
            self.template_type = _normalize_template_type(template_type)

        if language is not None:
            self.language = _validate_language(language)

        if is_active is not None:
            self.is_active = is_active

        if is_default is not None:
            self.is_default = is_default

        if variables_schema is not None:
            self.variables_schema = variables_schema

        self.updated_at = now

    def ensure_default_eligible(self) -> None:
        self.ensure_mutable()
        if not self.is_active:
            raise MailTemplateNotDefaultEligibleError("Inactive mail template cannot be default")

    def mark_as_default(self, *, now: datetime) -> None:
        self.ensure_default_eligible()
        self.is_default = True
        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        if self.deleted_at is not None:
            return
        self.deleted_at = now
        self.is_active = False
        self.is_default = False
        self.updated_at = now
