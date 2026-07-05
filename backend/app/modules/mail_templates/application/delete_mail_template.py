from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.mail_templates.application.commands import DeleteMailTemplateCommand, MailTemplateResult
from app.modules.mail_templates.application.mappers import mail_template_to_result
from app.modules.mail_templates.domain.exceptions import MailTemplateNotFoundError
from app.modules.mail_templates.domain.ports import MailTemplateRepository

PERMISSION_DELETE = "fair_crm.mail_templates.delete"


class DeleteMailTemplateUseCase:
    def __init__(
        self,
        repository: MailTemplateRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: DeleteMailTemplateCommand) -> MailTemplateResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        template = self._repository.get_by_id(command.organization_id, command.template_id)
        if template is None:
            raise MailTemplateNotFoundError("Mail template not found")

        now = datetime.now(tz=UTC)
        template.soft_delete(now=now)
        saved = self._repository.update(template)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.mail_template.deleted",
            resource_type="mail_template",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        return mail_template_to_result(saved)
