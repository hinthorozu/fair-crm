from app.modules.smtp.application.commands import ListSmtpAccountsQuery, SmtpAccountListResult
from app.modules.smtp.application.mappers import smtp_account_to_result
from app.modules.smtp.domain.ports import SmtpAccountRepository


class ListSmtpAccountsUseCase:
    def __init__(self, repository: SmtpAccountRepository) -> None:
        self._repository = repository

    def execute(self, query: ListSmtpAccountsQuery) -> SmtpAccountListResult:
        accounts = self._repository.list_by_organization(query.organization_id)
        return SmtpAccountListResult(items=[smtp_account_to_result(account) for account in accounts])
