from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.ports import FairRepository
from app.modules.participations.application.commands import CreateParticipationCommand, ParticipationResult
from app.modules.participations.application.mappers import participation_to_result, resolve_primary_contact_name
from app.modules.participations.application.validators import (
    ensure_customer_for_participation,
    ensure_fair_for_participation,
    ensure_no_duplicate_participation,
    validate_primary_contact,
)
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.ports import ParticipationRepository

PERMISSION_CREATE = "fair_crm.participations.create"


class CreateParticipationUseCase:
    def __init__(
        self,
        participation_repository: ParticipationRepository,
        customer_repository: CustomerRepository,
        fair_repository: FairRepository,
        contact_repository: ContactRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._participation_repository = participation_repository
        self._customer_repository = customer_repository
        self._fair_repository = fair_repository
        self._contact_repository = contact_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: CreateParticipationCommand) -> ParticipationResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_CREATE,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        ensure_customer_for_participation(
            self._customer_repository, command.organization_id, command.customer_id
        )
        ensure_fair_for_participation(self._fair_repository, command.organization_id, command.fair_id)
        validate_primary_contact(
            self._contact_repository,
            command.organization_id,
            command.customer_id,
            command.primary_contact_id,
        )
        ensure_no_duplicate_participation(
            self._participation_repository,
            command.organization_id,
            command.customer_id,
            command.fair_id,
        )

        now = datetime.now(tz=UTC)
        participation = CustomerFairParticipation.create(
            organization_id=command.organization_id,
            customer_id=command.customer_id,
            fair_id=command.fair_id,
            hall=command.hall,
            stand=command.stand,
            participation_status=command.participation_status,
            notes=command.notes,
            primary_contact_id=command.primary_contact_id,
            visited_at=command.visited_at,
            now=now,
        )
        saved = self._participation_repository.add(participation)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.participation.created",
            resource_type="customer_fair_participation",
            resource_id=str(saved.id),
            new_values={
                "customer_id": str(saved.customer_id),
                "fair_id": str(saved.fair_id),
            },
            metadata={"user_id": str(command.user_id)},
        )

        contact_name = resolve_primary_contact_name(
            self._participation_repository, command.organization_id, saved.primary_contact_id
        )
        return participation_to_result(saved, primary_contact_name=contact_name)
