from app.core.pagination import normalize_page_params, normalize_sort_direction
from app.modules.activities.application.commands import (
    ActivityListResultDto,
    ListActivitiesQuery,
)
from app.modules.activities.application.enrichment import enrich_activities
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.ports import CustomerRepository
from sqlalchemy.orm import Session

ALLOWED_SORT_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "activity_date",
        "follow_up_date",
        "subject",
        "status",
        "activity_type",
        "customer_name",
    }
)
DEFAULT_SORT_FIELD = "activity_date"
DEFAULT_SORT_DIRECTION = "desc"


class ListActivitiesUseCase:
    def __init__(
        self,
        activity_repository: ActivityRepository,
        customer_repository: CustomerRepository,
        contact_repository: ContactRepository,
        session: Session,
    ) -> None:
        self._activity_repository = activity_repository
        self._customer_repository = customer_repository
        self._contact_repository = contact_repository
        self._session = session

    def execute(self, query: ListActivitiesQuery) -> ActivityListResultDto:
        page_params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        result = self._activity_repository.list_all(
            query.organization_id,
            search=query.search,
            customer_id=query.customer_id,
            fair_id=query.fair_id,
            activity_type=query.activity_type,
            status=query.status,
            date_from=query.date_from,
            date_to=query.date_to,
            page=page_params.page,
            page_size=page_params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        items = enrich_activities(
            self._session,
            self._customer_repository,
            self._contact_repository,
            query.organization_id,
            result.items,
        )
        return ActivityListResultDto(
            items=items,
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        )
