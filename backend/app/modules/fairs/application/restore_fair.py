from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.fairs.application.commands import FairResult, RestoreFairCommand
from app.modules.fairs.application.mappers import fair_to_result
from app.modules.fairs.domain.exceptions import FairNotArchivedError, FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository

PERMISSION_RESTORE = "fair_crm.fairs.archive"


class RestoreFairUseCase:
    def __init__(
        self,
        repository: FairRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: RestoreFairCommand) -> FairResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_RESTORE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        fair = self._repository.get_by_id_including_archived(
            command.organization_id, command.fair_id
        )
        if fair is None:
            raise FairNotFoundError("Fair not found")

        now = datetime.now(tz=UTC)
        try:
            fair.restore(now=now)
        except FairNotArchivedError:
            raise

        saved = self._repository.update(fair)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.fair.restored",
            resource_type="fair",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        return fair_to_result(saved)
