from app.modules.mail_templates.application.commands import MailTemplateResult
from app.modules.mail_templates.domain.entities import MailTemplate


def mail_template_to_result(template: MailTemplate) -> MailTemplateResult:
    return MailTemplateResult(
        id=template.id,
        organization_id=template.organization_id,
        name=template.name,
        key=template.key,
        subject=template.subject,
        body_html=template.body_html,
        body_text=template.body_text,
        template_type=template.template_type,
        language=template.language,
        is_active=template.is_active,
        is_default=template.is_default,
        variables_schema=template.variables_schema,
        created_at=template.created_at,
        updated_at=template.updated_at,
        deleted_at=template.deleted_at,
    )
