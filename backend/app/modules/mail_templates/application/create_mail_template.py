from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.mail_templates.application.commands import CreateMailTemplateCommand, MailTemplateResult
from app.modules.mail_templates.application.mappers import mail_template_to_result
from app.modules.mail_templates.domain.entities import MailTemplate
from app.modules.mail_templates.domain.exceptions import MailTemplateKeyAlreadyExistsError
from app.modules.mail_templates.domain.ports import MailTemplateRepository

PERMISSION_CREATE = "fair_crm.mail_templates.create"


class CreateMailTemplateUseCase:
    def __init__(
        self,
        repository: MailTemplateRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateMailTemplateCommand) -> MailTemplateResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        existing = self._repository.get_by_key(command.organization_id, command.key)
        if existing is not None:
            raise MailTemplateKeyAlreadyExistsError("Mail template key already exists")

        now = datetime.now(tz=UTC)
        template = MailTemplate.create(
            organization_id=command.organization_id,
            name=command.name,
            key=command.key,
            subject=command.subject,
            body_html=command.body_html,
            body_text=command.body_text,
            template_type=command.template_type,
            language=command.language,
            is_active=command.is_active,
            is_default=command.is_default,
            variables_schema=command.variables_schema,
            now=now,
        )

        if template.is_default:
            self._repository.clear_default_for_type_language(
                command.organization_id,
                template.template_type.value,
                template.language,
            )
            self._repository.flush()

        saved = self._repository.add(template)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.mail_template.created",
            resource_type="mail_template",
            resource_id=str(saved.id),
            new_values={"name": saved.name, "key": saved.key},
            metadata={"user_id": str(command.user_id)},
        )

        return mail_template_to_result(saved)
