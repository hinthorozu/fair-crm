from app.modules.mail_templates.application.commands import GetMailTemplateQuery, MailTemplateResult
from app.modules.mail_templates.application.mappers import mail_template_to_result
from app.modules.mail_templates.domain.exceptions import MailTemplateNotFoundError
from app.modules.mail_templates.domain.ports import MailTemplateRepository


class GetMailTemplateUseCase:
    def __init__(self, repository: MailTemplateRepository) -> None:
        self._repository = repository

    def execute(self, query: GetMailTemplateQuery) -> MailTemplateResult:
        template = self._repository.get_by_id(query.organization_id, query.template_id)
        if template is None:
            raise MailTemplateNotFoundError("Mail template not found")
        return mail_template_to_result(template)
