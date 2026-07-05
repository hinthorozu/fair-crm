from app.modules.mail_templates.domain.entities import MailTemplate
from app.modules.mail_templates.domain.value_objects import MailTemplateType
from app.modules.mail_templates.infrastructure.persistence.models import MailTemplateModel


def model_to_entity(model: MailTemplateModel) -> MailTemplate:
    return MailTemplate(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        key=model.key,
        subject=model.subject,
        body_html=model.body_html,
        body_text=model.body_text,
        template_type=MailTemplateType(model.template_type),
        language=model.language,
        is_active=model.is_active,
        is_default=model.is_default,
        variables_schema=model.variables_schema,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def entity_to_model(template: MailTemplate) -> MailTemplateModel:
    return MailTemplateModel(
        id=template.id,
        organization_id=template.organization_id,
        name=template.name,
        key=template.key,
        subject=template.subject,
        body_html=template.body_html,
        body_text=template.body_text,
        template_type=template.template_type.value,
        language=template.language,
        is_active=template.is_active,
        is_default=template.is_default,
        variables_schema=template.variables_schema,
        created_at=template.created_at,
        updated_at=template.updated_at,
        deleted_at=template.deleted_at,
    )


def update_model_from_entity(model: MailTemplateModel, template: MailTemplate) -> None:
    model.name = template.name
    model.key = template.key
    model.subject = template.subject
    model.body_html = template.body_html
    model.body_text = template.body_text
    model.template_type = template.template_type.value
    model.language = template.language
    model.is_active = template.is_active
    model.is_default = template.is_default
    model.variables_schema = template.variables_schema
    model.updated_at = template.updated_at
    model.deleted_at = template.deleted_at
