from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.application.commands import DeleteActivityCommand
from app.modules.activities.domain.exceptions import ActivityNotFoundError
from app.modules.activities.domain.ports import ActivityRepository

PERMISSION_DELETE = "fair_crm.activities.delete"


class DeleteActivityUseCase:
    """Hard-delete a single activity (physical row removal). ADR-033."""

    def __init__(
        self,
        activity_repository: ActivityRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._activity_repository = activity_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: DeleteActivityCommand) -> None:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        activity = self._activity_repository.get_by_id(command.organization_id, command.activity_id)
        if activity is None:
            raise ActivityNotFoundError("Activity not found")

        deleted = self._activity_repository.hard_delete(
            command.organization_id, command.activity_id
        )
        if not deleted:
            raise ActivityNotFoundError("Activity not found")

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.activity.deleted",
            resource_type="activity",
            resource_id=str(command.activity_id),
            metadata={"user_id": str(command.user_id), "delete_mode": "hard"},
        )
