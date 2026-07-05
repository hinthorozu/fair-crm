from app.modules.mail_templates.application.commands import ListMailTemplatesQuery, MailTemplateListResult
from app.modules.mail_templates.application.mappers import mail_template_to_result
from app.modules.mail_templates.domain.ports import MailTemplateRepository


class ListMailTemplatesUseCase:
    def __init__(self, repository: MailTemplateRepository) -> None:
        self._repository = repository

    def execute(self, query: ListMailTemplatesQuery) -> MailTemplateListResult:
        templates = self._repository.list_by_organization(query.organization_id)
        return MailTemplateListResult(items=[mail_template_to_result(item) for item in templates])
