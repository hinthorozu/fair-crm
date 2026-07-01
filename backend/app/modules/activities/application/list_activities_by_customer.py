from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.activities.application.commands import ActivityListResultDto, ListActivitiesByCustomerQuery
from app.modules.activities.application.mappers import activity_to_result, resolve_contact_full_name
from app.modules.activities.application.validators import ensure_customer_for_activity
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.ports import CustomerRepository

ALLOWED_SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "activity_date",
        "follow_up_date",
        "subject",
        "status",
        "activity_type",
    }
)
DEFAULT_SORT_FIELD = "activity_date"
DEFAULT_SORT_DIRECTION = "desc"


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

        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._activity_repository.list_by_customer(
            query.organization_id,
            query.customer_id,
            search=query.search,
            activity_type=query.activity_type,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
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
