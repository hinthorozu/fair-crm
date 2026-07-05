from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.mail_templates.application.commands import RenderMailTemplateCommand, RenderMailTemplateResult
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateAlreadyDeletedError,
    MailTemplateNotFoundError,
    MailTemplateRenderError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository, MailTemplateRenderer

PERMISSION_RENDER = "fair_crm.mail_templates.render"


class RenderMailTemplateUseCase:
    def __init__(
        self,
        repository: MailTemplateRepository,
        renderer: MailTemplateRenderer,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._renderer = renderer
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: RenderMailTemplateCommand) -> RenderMailTemplateResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_RENDER,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        template = self._repository.get_by_id(command.organization_id, command.template_id)
        if template is None:
            raise MailTemplateNotFoundError("Mail template not found")
        if template.deleted_at is not None:
            raise MailTemplateAlreadyDeletedError("Mail template is deleted")

        try:
            rendered_subject = self._renderer.render(template.subject, command.variables)
            rendered_body_html = (
                self._renderer.render(template.body_html, command.variables)
                if template.body_html
                else None
            )
            rendered_body_text = (
                self._renderer.render(template.body_text, command.variables)
                if template.body_text
                else None
            )
        except MailTemplateRenderError:
            raise

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.mail_template.rendered",
            resource_type="mail_template",
            resource_id=str(template.id),
            metadata={"user_id": str(command.user_id)},
        )

        return RenderMailTemplateResult(
            subject=rendered_subject,
            body_html=rendered_body_html,
            body_text=rendered_body_text,
        )
