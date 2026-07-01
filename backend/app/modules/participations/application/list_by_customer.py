from app.modules.participations.application.commands import (
    CustomerParticipationListResultDto,
    ListParticipationsByCustomerQuery,
)
from app.modules.participations.application.mappers import customer_row_to_list_item, resolve_primary_contact_name
from app.modules.participations.application.validators import ensure_customer_for_participation
from app.modules.participations.domain.ports import ParticipationRepository
from app.modules.customers.domain.ports import CustomerRepository


class ListParticipationsByCustomerUseCase:
    def __init__(
        self,
        participation_repository: ParticipationRepository,
        customer_repository: CustomerRepository,
    ) -> None:
        self._participation_repository = participation_repository
        self._customer_repository = customer_repository

    def execute(self, query: ListParticipationsByCustomerQuery) -> CustomerParticipationListResultDto:
        ensure_customer_for_participation(
            self._customer_repository, query.organization_id, query.customer_id
        )

        result = self._participation_repository.list_by_customer(
            query.organization_id,
            query.customer_id,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
        )

        items = []
        for row in result.items:
            contact_name = resolve_primary_contact_name(
                self._participation_repository,
                query.organization_id,
                row.participation.primary_contact_id,
            )
            items.append(customer_row_to_list_item(row, primary_contact_name=contact_name))

        return CustomerParticipationListResultDto(
            items=items,
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        )
