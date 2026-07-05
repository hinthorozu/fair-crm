"""Repository for tenant-scoped mail template records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.mail_templates.domain.entities import MailTemplate
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateDefaultAlreadyExistsError,
    MailTemplateKeyAlreadyExistsError,
)
from app.modules.mail_templates.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.mail_templates.infrastructure.persistence.models import MailTemplateModel


class SqlAlchemyMailTemplateRepository:
    _DEFAULT_UNIQUE_INDEX = "uq_crm_mail_templates_org_type_lang_default"
    _KEY_UNIQUE_INDEX = "uq_crm_mail_templates_org_key"

    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def _raise_integrity_error(self, exc: IntegrityError) -> None:
        message = str(getattr(exc, "orig", exc)).lower()
        if self._DEFAULT_UNIQUE_INDEX in message or "is_default" in message:
            raise MailTemplateDefaultAlreadyExistsError(
                "Aynı tür ve dil için zaten varsayılan bir mail şablonu var."
            ) from exc
        if self._KEY_UNIQUE_INDEX in message or "org_key" in message or ".key" in message:
            raise MailTemplateKeyAlreadyExistsError("Mail template key already exists") from exc
        raise exc

    def add(self, template: MailTemplate) -> MailTemplate:
        model = entity_to_model(template)
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            self._raise_integrity_error(exc)
        return model_to_entity(model)

    def update(self, template: MailTemplate) -> MailTemplate:
        model = self._session.get(MailTemplateModel, template.id)
        if model is None:
            raise ValueError(f"Mail template not found: {template.id}")
        update_model_from_entity(model, template)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            self._raise_integrity_error(exc)
        return model_to_entity(model)

    def get_by_id(self, organization_id: UUID, template_id: UUID) -> MailTemplate | None:
        stmt = select(MailTemplateModel).where(
            MailTemplateModel.organization_id == organization_id,
            MailTemplateModel.id == template_id,
            MailTemplateModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        return model_to_entity(model) if model is not None else None

    def get_by_key(self, organization_id: UUID, key: str) -> MailTemplate | None:
        stmt = select(MailTemplateModel).where(
            MailTemplateModel.organization_id == organization_id,
            MailTemplateModel.key == key.strip().lower(),
            MailTemplateModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        return model_to_entity(model) if model is not None else None

    def list_by_organization(self, organization_id: UUID) -> list[MailTemplate]:
        stmt = (
            select(MailTemplateModel)
            .where(
                MailTemplateModel.organization_id == organization_id,
                MailTemplateModel.deleted_at.is_(None),
            )
            .order_by(MailTemplateModel.name.asc(), MailTemplateModel.id.asc())
        )
        return [model_to_entity(model) for model in self._session.scalars(stmt).all()]

    def clear_default_for_type_language(
        self,
        organization_id: UUID,
        template_type: str,
        language: str,
        *,
        exclude_template_id: UUID | None = None,
    ) -> None:
        stmt = select(MailTemplateModel).where(
            MailTemplateModel.organization_id == organization_id,
            MailTemplateModel.template_type == template_type,
            MailTemplateModel.language == language,
            MailTemplateModel.is_default.is_(True),
            MailTemplateModel.deleted_at.is_(None),
        )
        if exclude_template_id is not None:
            stmt = stmt.where(MailTemplateModel.id != exclude_template_id)
        for model in self._session.scalars(stmt).all():
            model.is_default = False
