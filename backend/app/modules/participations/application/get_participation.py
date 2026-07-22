from app.modules.participations.application.commands import GetParticipationQuery, ParticipationResult
from app.modules.participations.application.mappers import participation_to_result
from app.modules.participations.domain.exceptions import ParticipationNotFoundError
from app.modules.participations.domain.ports import ParticipationRepository


class GetParticipationUseCase:
    def __init__(self, participation_repository: ParticipationRepository) -> None:
        self._participation_repository = participation_repository

    def execute(self, query: GetParticipationQuery) -> ParticipationResult:
        participation = self._participation_repository.get_by_id(
            query.organization_id, query.participation_id
        )
        if participation is None:
            raise ParticipationNotFoundError("Participation not found")

        return participation_to_result(participation)
