from app.modules.activities.application.commands import ActivityListResultDto, ListActivitiesByCustomerQuery
from app.modules.activities.application.mappers import activity_to_result, resolve_contact_full_name
from app.modules.activities.application.validators import ensure_customer_for_activity
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.ports import CustomerRepository


class ListActivitiesByCustomerUseCase:
    def __init__(
        self,
        activity_repository: ActivityRepository,
        customer_repository: CustomerRepository,
        contact_repository: ContactRepository,
    ) -> None:
        self._activity_repository = activity_repository
        self._customer_repository = customer_repository
        self._contact_repository = contact_repository

    def execute(self, query: ListActivitiesByCustomerQuery) -> ActivityListResultDto:
        ensure_customer_for_activity(
            self._customer_repository, query.organization_id, query.customer_id
        )

        result = self._activity_repository.list_by_customer(
            query.organization_id,
            query.customer_id,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
        )

        items = []
        for activity in result.items:
            contact_full_name = resolve_contact_full_name(
                self._contact_repository, query.organization_id, activity.contact_id
            )
            items.append(activity_to_result(activity, contact_full_name=contact_full_name))

        return ActivityListResultDto(
            items=items,
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        )
