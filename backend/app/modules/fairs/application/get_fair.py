from app.modules.fairs.application.commands import FairResult, GetFairQuery
from app.modules.fairs.application.mappers import fair_to_result
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository


class GetFairUseCase:
    def __init__(self, repository: FairRepository) -> None:
        self._repository = repository

    def execute(self, query: GetFairQuery) -> FairResult:
        fair = self._repository.get_by_id(query.organization_id, query.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")
        return fair_to_result(fair)
