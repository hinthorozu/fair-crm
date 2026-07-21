from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.application.commands import (
    BulkDeleteActivitiesCommand,
    BulkDeleteActivitiesResult,
)
from app.modules.activities.domain.ports import ActivityRepository

PERMISSION_DELETE = "fair_crm.activities.delete"

MAX_BULK_DELETE_IDS = 200


class BulkDeleteActivitiesUseCase:
    """Hard-delete multiple activities in one transaction. ADR-033."""

    def __init__(
        self,
        activity_repository: ActivityRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._activity_repository = activity_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: BulkDeleteActivitiesCommand) -> BulkDeleteActivitiesResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_DELETE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        # Deduplicate while preserving order
        seen: set = set()
        unique_ids = []
        for activity_id in command.activity_ids:
            if activity_id in seen:
                continue
            seen.add(activity_id)
            unique_ids.append(activity_id)

        if len(unique_ids) > MAX_BULK_DELETE_IDS:
            unique_ids = unique_ids[:MAX_BULK_DELETE_IDS]

        existing = self._activity_repository.get_existing_ids(
            command.organization_id, unique_ids
        )
        existing_set = set(existing)
        deleted_ids = [aid for aid in unique_ids if aid in existing_set]
        not_found_ids = [aid for aid in unique_ids if aid not in existing_set]

        if deleted_ids:
            self._activity_repository.hard_delete_many(
                command.organization_id, deleted_ids
            )
            self._audit.record_event(
                organization_id=command.organization_id,
                access_token=command.access_token,
                action="fair_crm.activity.bulk_deleted",
                resource_type="activity",
                resource_id=",".join(str(i) for i in deleted_ids[:20]),
                metadata={
                    "user_id": str(command.user_id),
                    "delete_mode": "hard",
                    "deleted_count": len(deleted_ids),
                    "not_found_count": len(not_found_ids),
                },
            )

        return BulkDeleteActivitiesResult(
            deleted_ids=deleted_ids,
            not_found_ids=not_found_ids,
            deleted_count=len(deleted_ids),
            not_found_count=len(not_found_ids),
        )
