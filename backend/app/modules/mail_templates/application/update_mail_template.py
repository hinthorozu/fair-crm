from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.mail_templates.application.commands import MailTemplateResult, UpdateMailTemplateCommand
from app.modules.mail_templates.application.mappers import mail_template_to_result
from app.modules.mail_templates.domain.exceptions import (
    MailTemplateKeyAlreadyExistsError,
    MailTemplateNotFoundError,
)
from app.modules.mail_templates.domain.ports import MailTemplateRepository

PERMISSION_UPDATE = "fair_crm.mail_templates.update"


class UpdateMailTemplateUseCase:
    def __init__(
        self,
        repository: MailTemplateRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateMailTemplateCommand) -> MailTemplateResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        template = self._repository.get_by_id(command.organization_id, command.template_id)
        if template is None:
            raise MailTemplateNotFoundError("Mail template not found")

        if command.key is not None and command.key.strip().lower() != template.key:
            existing = self._repository.get_by_key(command.organization_id, command.key)
            if existing is not None and existing.id != template.id:
                raise MailTemplateKeyAlreadyExistsError("Mail template key already exists")

        now = datetime.now(tz=UTC)
        was_default = template.is_default
        is_default_update = command.is_default

        template.update_fields(
            name=command.name,
            key=command.key,
            subject=command.subject,
            body_html=command.body_html,
            body_text=command.body_text,
            template_type=command.template_type,
            language=command.language,
            is_active=command.is_active,
            is_default=None,
            variables_schema=command.variables_schema,
            now=now,
        )

        will_be_default = is_default_update if is_default_update is not None else was_default

        if will_be_default:
            template.ensure_default_eligible()
            self._repository.clear_default_for_type_language(
                command.organization_id,
                template.template_type.value,
                template.language,
                exclude_template_id=template.id,
            )
            self._repository.flush()
            template.mark_as_default(now=now)
        elif is_default_update is False:
            template.is_default = False
            template.updated_at = now

        saved = self._repository.update(template)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.mail_template.updated",
            resource_type="mail_template",
            resource_id=str(saved.id),
            new_values={"name": saved.name, "key": saved.key},
            metadata={"user_id": str(command.user_id)},
        )

        return mail_template_to_result(saved)
