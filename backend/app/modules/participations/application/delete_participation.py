from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.participations.application.commands import DeleteParticipationCommand, ParticipationResult
from app.modules.participations.application.mappers import participation_to_result
from app.modules.participations.domain.exceptions import ParticipationNotFoundError
from app.modules.participations.domain.ports import ParticipationRepository

PERMISSION_DELETE = "fair_crm.participations.delete"


class DeleteParticipationUseCase:
    def __init__(
        self,
        participation_repository: ParticipationRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._participation_repository = participation_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: DeleteParticipationCommand) -> ParticipationResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        participation = self._participation_repository.get_by_id(
            command.organization_id, command.participation_id
        )
        if participation is None:
            raise ParticipationNotFoundError("Participation not found")

        now = datetime.now(tz=UTC)
        participation.soft_delete(now=now)
        saved = self._participation_repository.update(participation)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.participation.deleted",
            resource_type="customer_fair_participation",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        return participation_to_result(saved)
