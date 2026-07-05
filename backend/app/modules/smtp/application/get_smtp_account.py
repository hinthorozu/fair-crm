from app.modules.smtp.application.commands import GetSmtpAccountQuery, SmtpAccountResult
from app.modules.smtp.application.mappers import smtp_account_to_result
from app.modules.smtp.domain.exceptions import SmtpAccountNotFoundError
from app.modules.smtp.domain.ports import SmtpAccountRepository


class GetSmtpAccountUseCase:
    def __init__(self, repository: SmtpAccountRepository) -> None:
        self._repository = repository

    def execute(self, query: GetSmtpAccountQuery) -> SmtpAccountResult:
        account = self._repository.get_by_id(query.organization_id, query.account_id)
        if account is None:
            raise SmtpAccountNotFoundError("SMTP account not found")
        return smtp_account_to_result(account)
