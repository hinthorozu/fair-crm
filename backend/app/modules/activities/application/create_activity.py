from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.application.commands import ActivityResult, CreateActivityCommand
from app.modules.activities.application.mappers import activity_to_result, resolve_contact_full_name
from app.modules.activities.application.validators import (
    ensure_customer_for_activity,
    validate_contact_for_activity,
)
from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.ports import CustomerRepository

PERMISSION_CREATE = "fair_crm.activities.create"


class CreateActivityUseCase:
    def __init__(
        self,
        activity_repository: ActivityRepository,
        customer_repository: CustomerRepository,
        contact_repository: ContactRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._activity_repository = activity_repository
        self._customer_repository = customer_repository
        self._contact_repository = contact_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateActivityCommand) -> ActivityResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        ensure_customer_for_activity(
            self._customer_repository, command.organization_id, command.customer_id
        )
        validate_contact_for_activity(
            self._contact_repository,
            command.organization_id,
            command.customer_id,
            command.contact_id,
        )

        now = datetime.now(tz=UTC)
        activity = Activity.create(
            organization_id=command.organization_id,
            customer_id=command.customer_id,
            contact_id=command.contact_id,
            activity_type=command.activity_type,
            subject=command.subject,
            description=command.description,
            activity_date=command.activity_date,
            follow_up_date=command.follow_up_date,
            status=command.status,
            source=command.source,
            is_active=command.is_active,
            now=now,
        )

        saved = self._activity_repository.add(activity)

        contact_full_name = resolve_contact_full_name(
            self._contact_repository, command.organization_id, saved.contact_id
        )

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.activity.created",
            resource_type="activity",
            resource_id=str(saved.id),
            new_values={"subject": saved.subject, "customer_id": str(saved.customer_id)},
            metadata={"user_id": str(command.user_id)},
        )

        return activity_to_result(saved, contact_full_name=contact_full_name)
