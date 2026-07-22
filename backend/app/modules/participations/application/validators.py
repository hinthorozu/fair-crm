from uuid import UUID

from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.ports import FairRepository
from app.modules.participations.domain.exceptions import (
    CustomerArchivedForParticipationError,
    CustomerNotFoundForParticipationError,
    DuplicateParticipationError,
    FairArchivedForParticipationError,
    FairNotFoundForParticipationError,
)
from app.modules.participations.domain.ports import ParticipationRepository


def ensure_customer_for_participation(
    customer_repository: CustomerRepository,
    organization_id: UUID,
    customer_id: UUID,
) -> Customer:
    customer = customer_repository.get_by_id_including_archived(organization_id, customer_id)
    if customer is None:
        raise CustomerNotFoundForParticipationError("Customer not found")
    if customer.is_merge_deleted():
        raise CustomerArchivedForParticipationError("Customer is deleted")
    if customer.is_archived():
        raise CustomerArchivedForParticipationError("Customer is archived")
    return customer


def ensure_fair_for_participation(
    fair_repository: FairRepository,
    organization_id: UUID,
    fair_id: UUID,
) -> Fair:
    fair = fair_repository.get_by_id_including_archived(organization_id, fair_id)
    if fair is None:
        raise FairNotFoundForParticipationError("Fair not found")
    if fair.is_archived():
        raise FairArchivedForParticipationError("Fair is archived")
    return fair


def ensure_no_duplicate_participation(
    participation_repository: ParticipationRepository,
    organization_id: UUID,
    customer_id: UUID,
    fair_id: UUID,
) -> None:
    if participation_repository.exists_active(organization_id, customer_id, fair_id):
        raise DuplicateParticipationError("Active participation already exists for this customer and fair")
