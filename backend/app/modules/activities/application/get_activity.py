from sqlalchemy.orm import Session

from app.modules.activities.application.commands import ActivityResult, GetActivityQuery
from app.modules.activities.application.enrichment import enrich_activities
from app.modules.activities.domain.exceptions import ActivityNotFoundError
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.ports import CustomerRepository


class GetActivityUseCase:
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

    def execute(self, query: GetActivityQuery) -> ActivityResult:
        activity = self._activity_repository.get_by_id(query.organization_id, query.activity_id)
        if activity is None:
            raise ActivityNotFoundError("Activity not found")

        items = enrich_activities(
            self._session,
            self._customer_repository,
            self._contact_repository,
            query.organization_id,
            [activity],
        )
        return items[0]
