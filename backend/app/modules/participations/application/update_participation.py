from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.participations.application.commands import ParticipationResult, UpdateParticipationCommand
from app.modules.participations.application.mappers import participation_to_result, resolve_primary_contact_name
from app.modules.participations.application.validators import validate_primary_contact
from app.modules.participations.domain.exceptions import ParticipationNotFoundError
from app.modules.participations.domain.ports import ParticipationRepository

PERMISSION_UPDATE = "fair_crm.participations.update"


class UpdateParticipationUseCase:
    def __init__(
        self,
        participation_repository: ParticipationRepository,
        contact_repository: ContactRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._participation_repository = participation_repository
        self._contact_repository = contact_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: UpdateParticipationCommand) -> ParticipationResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_UPDATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        participation = self._participation_repository.get_by_id(
            command.organization_id, command.participation_id
        )
        if participation is None:
            raise ParticipationNotFoundError("Participation not found")

        contact_id = command.primary_contact_id if command.set_primary_contact_id else participation.primary_contact_id
        if command.set_primary_contact_id or command.primary_contact_id is not None:
            validate_primary_contact(
                self._contact_repository,
                command.organization_id,
                participation.customer_id,
                contact_id,
            )

        now = datetime.now(tz=UTC)
        participation.update_fields(
            now=now,
            hall=command.hall,
            stand=command.stand,
            participation_status=command.participation_status,
            notes=command.notes,
            primary_contact_id=command.primary_contact_id,
            visited_at=command.visited_at,
            is_active=command.is_active,
            set_hall=command.set_hall,
            set_stand=command.set_stand,
            set_notes=command.set_notes,
            set_primary_contact_id=command.set_primary_contact_id,
            set_visited_at=command.set_visited_at,
        )
        saved = self._participation_repository.update(participation)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.participation.updated",
            resource_type="customer_fair_participation",
            resource_id=str(saved.id),
            metadata={"user_id": str(command.user_id)},
        )

        contact_name = resolve_primary_contact_name(
            self._participation_repository, command.organization_id, saved.primary_contact_id
        )
        return participation_to_result(saved, primary_contact_name=contact_name)
