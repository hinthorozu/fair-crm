from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.application.commands import ActivityResult, UpdateActivityCommand
from app.modules.activities.application.mappers import activity_to_result, resolve_contact_full_name
from app.modules.activities.application.validators import validate_contact_for_activity
from app.modules.activities.domain.exceptions import ActivityNotFoundError
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.contacts.domain.ports import ContactRepository

PERMISSION_UPDATE = "fair_crm.activities.update"


class UpdateActivityUseCase:
    def __init__(
        self,
        activity_repository: ActivityRepository,
        contact_repository: ContactRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._activity_repository = activity_repository
        self._contact_repository = contact_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateActivityCommand) -> ActivityResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        activity = self._activity_repository.get_by_id(command.organization_id, command.activity_id)
        if activity is None:
            raise ActivityNotFoundError("Activity not found")

        contact_id = command.contact_id if command.set_contact_id else activity.contact_id
        validate_contact_for_activity(
            self._contact_repository,
            command.organization_id,
            activity.customer_id,
            contact_id,
        )

        now = datetime.now(tz=UTC)
        activity.update_fields(
            now=now,
            contact_id=command.contact_id,
            activity_type=command.activity_type,
            subject=command.subject,
            description=command.description,
            activity_date=command.activity_date,
            follow_up_date=command.follow_up_date,
            status=command.status,
            source=command.source,
            is_active=command.is_active,
            set_contact_id=command.set_contact_id,
            set_description=command.set_description,
            set_follow_up_date=command.set_follow_up_date,
        )

        saved = self._activity_repository.update(activity)

        contact_full_name = resolve_contact_full_name(
            self._contact_repository, command.organization_id, saved.contact_id
        )

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.activity.updated",
            resource_type="activity",
            resource_id=str(saved.id),
            new_values={"subject": saved.subject},
            metadata={"user_id": str(command.user_id)},
        )

        return activity_to_result(saved, contact_full_name=contact_full_name)
